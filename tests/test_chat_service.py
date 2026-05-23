import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import chat_service
from app.services.chat_service import (
    PersistenceRetryExhausted,
    ScopeResolutionError,
    UnknownBotError,
)


@asynccontextmanager
async def _dummy_session():
    yield object()


async def test_scope_resolution_failure() -> None:
    try:
        await chat_service.get_reply(
            bot_id="bot-1",
            user_id=1,
            user_message="hello",
            chat_id=None,
            request_context=None,
        )
    except ScopeResolutionError:
        return
    raise AssertionError("Expected ScopeResolutionError")


async def test_unknown_bot_failure() -> None:
    with patch.object(chat_service, "get_session", _dummy_session):
        with patch.object(chat_service.bot_repo, "get_by_bot_id", AsyncMock(return_value=None)):
            try:
                await chat_service.get_reply(
                    bot_id="missing",
                    user_id=1,
                    user_message="hello",
                    chat_id=123,
                )
            except UnknownBotError:
                return
    raise AssertionError("Expected UnknownBotError")


async def test_retry_exhausted_failure() -> None:
    fake_bot = SimpleNamespace(persona_config={})

    with patch.object(chat_service, "get_session", _dummy_session):
        with patch.object(chat_service.bot_repo, "get_by_bot_id", AsyncMock(return_value=fake_bot)):
            with patch.object(chat_service.relationship_repo, "ensure_relationship", AsyncMock(return_value=None)):
                with patch.object(
                    chat_service,
                    "_load_history",
                    AsyncMock(side_effect=PersistenceRetryExhausted("failed")),
                ):
                    try:
                        await chat_service.get_reply(
                            bot_id="bot-1",
                            user_id=1,
                            user_message="hello",
                            chat_id=123,
                        )
                    except PersistenceRetryExhausted:
                        return
    raise AssertionError("Expected PersistenceRetryExhausted")


async def main() -> None:
    await test_scope_resolution_failure()
    await test_unknown_bot_failure()
    await test_retry_exhausted_failure()


if __name__ == "__main__":
    asyncio.run(main())
