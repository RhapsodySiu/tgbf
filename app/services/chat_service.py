from typing import Any
import logging
import asyncio
from time import time

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
PERSONA_CACHE_TTL_SECONDS = 300


class ScopeResolutionError(Exception):
    pass


class UnknownBotError(Exception):
    pass


class PersistenceRetryExhausted(Exception):
    pass


# Persona cache: {bot_id: (bot_record, inserted_at)}
_persona_cache: dict[int, tuple[Bot, float]] = {}
_persona_cache_lock = asyncio.Lock()


async def _get_persona_cached(bot_id: int) -> Bot | None:
    """Resolve persona for bot_id: cache first (TTL lazy eviction), then DB fallback."""
    async with _persona_cache_lock:
        if bot_id in _persona_cache:
            bot, inserted_at = _persona_cache[bot_id]
            age_seconds = time() - inserted_at
            if age_seconds < PERSONA_CACHE_TTL_SECONDS:
                # Cache hit within TTL
                logger.info("persona_resolved", extra={"bot_id": bot_id, "outcome": "cache_hit", **get_log_context()})
                return bot
            else:
                # Expired; remove from cache
                del _persona_cache[bot_id]
    
    # Cache miss or expired: query DB
    async with get_session() as session:
        bot = await bot_repo.get_by_bot_id(session, bot_id)
    
    if bot is None:
        logger.info("persona_resolved", extra={"bot_id": bot_id, "outcome": "not_found", **get_log_context()})
        return None
    
    # Populate cache
    async with _persona_cache_lock:
        _persona_cache[bot_id] = (bot, time())
    
    logger.info("persona_resolved", extra={"bot_id": bot_id, "outcome": "db_hit", **get_log_context()})
    return bot


def _assert_scope(*, bot_id: int | None, chat_id: int | None, user_id: int | None) -> None:
    """Service-layer scope assertion: verify all scope fields are present and valid."""
    if bot_id is None or chat_id is None or user_id is None:
        logger.info("scope_assertion_failed", extra={"outcome": "missing_field", **get_log_context()})
        raise ScopeResolutionError("Scope context incomplete (bot_id, chat_id, user_id required)")


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


async def _load_history(
    *,
    bot_id: int,
    chat_id: int,
    user_id: int,
    limit: int,
) -> list[Message]:
    """Load message history for scoped context (no retry: fail-fast per Unit C design)."""
    async with get_session() as session:
        return await message_repo.get_recent_for_context(
            session,
            bot_id,
            chat_id,
            user_id,
            limit,
        )


async def get_reply(
    *,
    bot_id: int,
    user_id: int,
    user_message: str,
    chat_id: int | None = None,
    dedup_key: str | None = None,
    request_context: dict[str, Any] | None = None,
) -> str:
    # Resolve and validate scope
    resolved_chat_id = _resolve_chat_id(chat_id, request_context)
    _assert_scope(bot_id=bot_id, chat_id=resolved_chat_id, user_id=user_id)

    # Resolve persona: cache-first, fail-fast on miss
    persona = await _get_persona_cached(bot_id)
    if persona is None:
        logger.info("bot_resolution_failed", extra={"bot_id": bot_id, **get_log_context()})
        raise UnknownBotError(f"Unknown bot_id: {bot_id}")

    # Ensure relationship
    async with get_session() as session:
        await relationship_repo.ensure_relationship(session, bot_id, user_id)

    # Load history (no retry)
    try:
        histories = await _load_history(
            bot_id=bot_id,
            chat_id=resolved_chat_id,
            user_id=user_id,
            limit=HISTORY_MAX_SIZE,
        )
    except Exception as exc:
        logger.error("history_retrieval_failed", exc_info=True, extra={"bot_id": bot_id, **get_log_context()})
        raise PersistenceRetryExhausted("History retrieval failed") from exc

    # Save inbound message
    async with get_session() as session:
        await message_repo.save_inbound(
            session,
            bot_id,
            resolved_chat_id,
            user_id,
            user_message,
            dedup_key=dedup_key,
        )

    # Build LLM payload
    history_payload = build_history_payload(histories)
    persona_config = persona.persona_config or {}
    messages = [
        {
            "role": "system",
            "content": build_system_prompt("Test", persona_config),
        },
        *history_payload,
        {
            "role": "user",
            "content": user_message,
        },
    ]

    # Call LLM
    reply = await llm.chat(messages)

    # Save outbound response
    async with get_session() as session:
        await message_repo.save_outbound(
            session,
            bot_id,
            resolved_chat_id,
            user_id,
            reply,
        )

    logger.info("reply_generated", extra={"bot_id": bot_id, "outcome": "success", **get_log_context()})
    return reply

