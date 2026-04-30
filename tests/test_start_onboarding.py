from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.handlers import commands


@asynccontextmanager
async def _dummy_session():
    yield object()


def _fake_message(text: str, user_id: int = 100, username: str | None = "alice", first_name: str | None = "Alice"):
    msg = SimpleNamespace()
    msg.text = text
    msg.from_user = SimpleNamespace(id=user_id, username=username, first_name=first_name)
    msg.answer = AsyncMock()
    return msg


async def test_start_no_token_returns_generic_welcome() -> None:
    message = _fake_message("/start")

    await commands.cmd_start(message)

    message.answer.assert_awaited_once_with(commands.NO_TOKEN_WELCOME_MESSAGE, parse_mode=None)


async def test_start_invalid_token_returns_invalid_message() -> None:
    message = _fake_message("/start bad-token")

    with patch.object(commands, "get_session", _dummy_session):
        with patch.object(commands.user_repo, "get_by_invite_token", AsyncMock(return_value=None)):
            await commands.cmd_start(message)

    message.answer.assert_awaited_once_with(commands.INVALID_INVITE_MESSAGE, parse_mode=None)


async def test_start_user_id_mismatch_returns_invalid_message() -> None:
    message = _fake_message("/start token-1", user_id=111)
    found_user = SimpleNamespace(user_id=222, is_allowed=False, joined_at=None)

    with patch.object(commands, "get_session", _dummy_session):
        with patch.object(commands.user_repo, "get_by_invite_token", AsyncMock(return_value=found_user)):
            await commands.cmd_start(message)

    message.answer.assert_awaited_once_with(commands.INVALID_INVITE_MESSAGE, parse_mode=None)


async def test_start_first_time_onboarding_sets_allowed_and_joined_at() -> None:
    message = _fake_message("/start token-1", user_id=123, username="newname", first_name="Nora")
    found_user = SimpleNamespace(user_id=123, is_allowed=False, joined_at=None)

    with patch.object(commands, "get_session", _dummy_session):
        with patch.object(commands.user_repo, "get_by_invite_token", AsyncMock(return_value=found_user)):
            update_mock = AsyncMock()
            with patch.object(commands.user_repo, "update", update_mock):
                await commands.cmd_start(message)

    update_args = update_mock.await_args.args
    assert update_args[1] == 123
    payload = update_args[2]
    assert payload["is_allowed"] is True
    assert payload["username"] == "newname"
    assert payload["first_name"] == "Nora"
    assert isinstance(payload["joined_at"], datetime)
    message.answer.assert_awaited_once_with("Welcome, Nora! You can now chat.", parse_mode=None)


async def test_start_idempotent_reuse_welcomes_back_without_joined_at_reset() -> None:
    message = _fake_message("/start token-1", user_id=123, username="newname", first_name="Nora")
    joined_at = datetime(2025, 1, 1)
    found_user = SimpleNamespace(user_id=123, is_allowed=True, joined_at=joined_at)

    with patch.object(commands, "get_session", _dummy_session):
        with patch.object(commands.user_repo, "get_by_invite_token", AsyncMock(return_value=found_user)):
            update_mock = AsyncMock()
            with patch.object(commands.user_repo, "update", update_mock):
                await commands.cmd_start(message)

    payload = update_mock.await_args.args[2]
    assert "is_allowed" not in payload
    assert "joined_at" not in payload
    message.answer.assert_awaited_once_with("Welcome back, Nora! You're all set.", parse_mode=None)


async def test_start_db_failure_returns_generic_failure() -> None:
    message = _fake_message("/start token-1")

    with patch.object(commands, "get_session", _dummy_session):
        with patch.object(commands.user_repo, "get_by_invite_token", AsyncMock(side_effect=RuntimeError("db down"))):
            await commands.cmd_start(message)

    message.answer.assert_awaited_once_with(commands.GENERIC_FAILURE_MESSAGE, parse_mode=None)
