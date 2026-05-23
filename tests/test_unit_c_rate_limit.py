"""Unit tests for Unit C rate limiting (middleware quota gate)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from app.middlewares.allowlist import AllowlistMiddleware, _quota_counters


@pytest.fixture
async def middleware():
    """AllowlistMiddleware fixture."""
    with patch("app.middlewares.allowlist.UserRepository"):
        return AllowlistMiddleware()


@pytest.fixture
def telegram_message():
    """Create a mock Telegram message."""
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 456
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = 123
    msg.bot = MagicMock()
    msg.bot.id = 777
    msg.text = "hello"
    msg.message_id = 999
    msg.answer = AsyncMock()  # Async mock for answer
    return msg


@pytest.mark.asyncio
async def test_quota_gate_allows_under_limit(middleware, telegram_message):
    """Request allowed if under per-bot-user quota."""
    # Clear previous counters
    _quota_counters.clear()
    
    # Call _check_quota multiple times (under limit of 100)
    for i in range(5):
        result = await middleware._check_quota(bot_id=777, user_id=456)
        assert result is True, f"Request {i+1} should be allowed"


@pytest.mark.asyncio
async def test_quota_gate_rejects_over_limit(middleware, telegram_message):
    """Request rejected if over per-bot-user quota."""
    # Clear and pre-populate counter to just below limit
    _quota_counters.clear()
    import time
    current_minute = int(time.time() // 60)
    _quota_counters[(777, 456, current_minute)] = 100
    
    # Next request should be rejected
    result = await middleware._check_quota(bot_id=777, user_id=456)
    assert result is False, "Request over quota should be rejected"


@pytest.mark.asyncio
async def test_quota_counters_isolated_by_bot_and_user(middleware):
    """Rate limits are independent per (bot_id, user_id) tuple."""
    _quota_counters.clear()
    
    # Fill quota for bot 777, user 456
    for i in range(100):
        await middleware._check_quota(bot_id=777, user_id=456)
    
    # Verify next request to same (bot, user) is rejected
    result_same = await middleware._check_quota(bot_id=777, user_id=456)
    assert result_same is False
    
    # Verify request to different bot (888, same user) is still allowed
    result_diff_bot = await middleware._check_quota(bot_id=888, user_id=456)
    assert result_diff_bot is True
    
    # Verify request to same bot (777), different user (789) is still allowed
    result_diff_user = await middleware._check_quota(bot_id=777, user_id=789)
    assert result_diff_user is True


@pytest.mark.asyncio
async def test_quota_message_explicit_throttle_response(middleware, telegram_message):
    """User receives explicit throttle message on quota breach."""
    _quota_counters.clear()
    
    # Pre-fill quota to limit
    import time
    current_minute = int(time.time() // 60)
    _quota_counters[(777, 456, current_minute)] = 100
    
    # Mock handler to track if it's called
    handler_called = False
    async def mock_handler(event, data):
        nonlocal handler_called
        handler_called = True
        return "ok"
    
    # Mock event_from_user
    data = {
        "event_from_user": telegram_message.from_user,
    }
    
    # Call middleware
    result = await middleware(mock_handler, telegram_message, data)
    
    # Handler should NOT be called
    assert not handler_called
    
    # Message.answer should have been called with throttle message
    telegram_message.answer.assert_called_once()
    args, kwargs = telegram_message.answer.call_args
    assert "too quickly" in args[0].lower() or "throttl" in args[0].lower()


@pytest.mark.asyncio
async def test_quota_counter_cleanup_old_minutes(middleware):
    """Old minute counters are cleaned up."""
    _quota_counters.clear()
    
    import time
    current_minute = int(time.time() // 60)
    
    # Populate counters for old minutes
    _quota_counters[(777, 456, current_minute - 3)] = 50
    _quota_counters[(777, 456, current_minute - 2)] = 60
    _quota_counters[(777, 456, current_minute - 1)] = 70
    _quota_counters[(777, 456, current_minute)] = 80
    
    # Call _check_quota (triggers cleanup)
    await middleware._check_quota(bot_id=777, user_id=456)
    
    # Verify old entries are removed (older than current_minute - 1)
    remaining_keys = [(k[0], k[1], k[2]) for k in _quota_counters.keys() if k[0] == 777 and k[1] == 456]
    
    # Should only have current minute and current_minute - 1 (for cleanup window)
    for key in remaining_keys:
        assert key[2] >= current_minute - 1, f"Old minute key {key} should be cleaned up"
