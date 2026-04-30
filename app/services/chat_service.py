from typing import Any
import logging

from tenacity import AsyncRetrying, stop_after_attempt

from app.db.models.bot import Bot
from app.db.models.message import Direction, Message
from app.db.models.relationship import Relationship
from app.db.repositories.bot import BotRepository
from app.db.repositories.message import ChatMessageRepository
from app.db.repositories.relationship import RelationshipRepository
from app.db.session import get_session
from app.llm.adapter import llm
from app.llm.prompts import build_system_prompt
from app.services.log_context import get_log_context

logger = logging.getLogger(__name__)

bot_repo = BotRepository(Bot)
message_repo = ChatMessageRepository(Message)
relationship_repo = RelationshipRepository(Relationship)

HISTORY_MAX_SIZE = 20

class ScopeResolutionError(Exception):
    pass


class UnknownBotError(Exception):
    pass


class PersistenceRetryExhausted(Exception):
    pass


def _resolve_chat_id(chat_id: int | None, request_context: dict[str, Any] | None) -> int | None:
    if chat_id is not None:
        return chat_id
    if request_context is None:
        return None
    return request_context.get("chat_id")


def map_message_to_chat_payload(message: Message) -> dict[str, str] | None:
    content = (message.content or "").strip()
    if not content:
        return None

    role = "assistant" if message.direction == Direction.OUTBOUND else "user"
    return {
        "role": role,
        "content": content,
    }


def build_history_payload(messages: list[Message]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for message in messages:
        mapped = map_message_to_chat_payload(message)
        if mapped is not None:
            payload.append(mapped)
    return payload


async def _load_history_with_retry(
    *,
    bot_id: str,
    chat_id: int,
    user_id: int,
    limit: int,
) -> list[Message]:
    attempts = 0

    try:
        async for attempt in AsyncRetrying(stop=stop_after_attempt(2), reraise=True):
            with attempt:
                attempts += 1
                if attempts > 1:
                    logger.info(
                        "persistence_retry_attempt",
                        extra={"attempt": attempts, **get_log_context()},
                    )
                async with get_session() as session:
                    return await message_repo.get_recent_for_context(
                        session,
                        bot_id,
                        chat_id,
                        user_id,
                        limit,
                    )
    except Exception as exc:
        logger.error("retry_exhausted", exc_info=True, extra=get_log_context())
        raise PersistenceRetryExhausted("History retrieval failed after retry") from exc

    return []


async def get_reply(
    *,
    bot_id: str,
    user_id: int,
    user_message: str,
    chat_id: int | None = None,
    dedup_key: str | None = None,
    request_context: dict[str, Any] | None = None,
) -> str:
    resolved_chat_id = _resolve_chat_id(chat_id, request_context)
    if resolved_chat_id is None:
        logger.warning(
            "scope_resolution_failure",
            extra={"reason": "chat_id_missing", "bot_id": bot_id, "user_id": user_id},
        )
        raise ScopeResolutionError("chat_id could not be resolved")

    async with get_session() as session:
        bot = await bot_repo.get_by_bot_id(session, bot_id)
        if bot is None:
            logger.warning("unknown_bot_rejected", extra={"bot_id": bot_id, **get_log_context()})
            raise UnknownBotError(f"Unknown bot_id: {bot_id}")

        await relationship_repo.ensure_relationship(session, bot_id, user_id)

    histories = await _load_history_with_retry(
        bot_id=bot_id,
        chat_id=resolved_chat_id,
        user_id=user_id,
        limit=HISTORY_MAX_SIZE,
    )

    async with get_session() as session:
        await message_repo.save_inbound(
            session,
            bot_id,
            resolved_chat_id,
            user_id,
            user_message,
            dedup_key=dedup_key,
        )

    history_payload = build_history_payload(histories)
    persona = bot.persona_config or {}
    messages = [
        {
            "role": "system",
            "content": build_system_prompt("Test", persona),
        },
        *history_payload,
        {
            "role": "user",
            "content": user_message,
        },
    ]

    reply = await llm.chat(messages)

    async with get_session() as session:
        await message_repo.save_outbound(
            session,
            bot_id,
            resolved_chat_id,
            user_id,
            reply,
        )

    return reply


