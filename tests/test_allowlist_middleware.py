from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.middlewares import allowlist
from app.middlewares.allowlist import AllowlistMiddleware


@asynccontextmanager
async def _dummy_session():
    yield object()


class FakeMessage:
    def __init__(self, text: str):
        self.text = text
        self.answer = AsyncMock()


async def _dummy_handler(event, data):
    return "handled"


async def test_start_bypasses_allowlist_check() -> None:
    middleware = AllowlistMiddleware()
    event = FakeMessage("/start token-1")
    data = {"event_from_user": SimpleNamespace(id=10)}

    with patch.object(allowlist, "Message", FakeMessage):
        with patch.object(allowlist, "get_session", _dummy_session):
            with patch.object(middleware.user_repo, "get_by_id", AsyncMock(side_effect=AssertionError("should not query"))):
                result = await middleware(_dummy_handler, event, data)

    assert result == "handled"
    event.answer.assert_not_awaited()


async def test_non_start_denied_for_unallowed_user() -> None:
    middleware = AllowlistMiddleware()
    event = FakeMessage("hello")
    data = {"event_from_user": SimpleNamespace(id=10)}

    with patch.object(allowlist, "Message", FakeMessage):
        with patch.object(allowlist, "get_session", _dummy_session):
            found_user = SimpleNamespace(is_allowed=False)
            with patch.object(middleware.user_repo, "get_by_id", AsyncMock(return_value=found_user)):
                result = await middleware(_dummy_handler, event, data)

    assert result is None
    event.answer.assert_awaited_once_with(
        "Access denied. Please complete onboarding with /start <invite_token>.",
        parse_mode=None,
    )


async def test_non_start_allowed_user_reaches_handler() -> None:
    middleware = AllowlistMiddleware()
    event = FakeMessage("hello")
    data = {"event_from_user": SimpleNamespace(id=10)}

    with patch.object(allowlist, "Message", FakeMessage):
        with patch.object(allowlist, "get_session", _dummy_session):
            found_user = SimpleNamespace(is_allowed=True)
            with patch.object(middleware.user_repo, "get_by_id", AsyncMock(return_value=found_user)):
                result = await middleware(_dummy_handler, event, data)

    assert result == "handled"
    event.answer.assert_not_awaited()


async def test_middleware_db_failure_fails_closed_with_error_message() -> None:
    middleware = AllowlistMiddleware()
    event = FakeMessage("hello")
    data = {"event_from_user": SimpleNamespace(id=10)}

    with patch.object(allowlist, "Message", FakeMessage):
        with patch.object(allowlist, "get_session", _dummy_session):
            with patch.object(middleware.user_repo, "get_by_id", AsyncMock(side_effect=RuntimeError("db error"))):
                result = await middleware(_dummy_handler, event, data)

    assert result is None
    event.answer.assert_awaited_once_with("Service temporarily unavailable. Please try again.", parse_mode=None)
