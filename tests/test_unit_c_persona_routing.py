"""Unit tests for Unit C persona routing and isolation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat_service import (
    get_reply,
    ScopeResolutionError,
    UnknownBotError,
    PersistenceRetryExhausted,
    _assert_scope,
    _get_persona_cached,
)
from app.db.models.bot import Bot
from app.db.models.message import Message, Direction


@pytest.fixture
def mock_bot_a():
    """Bot A persona fixture."""
    bot = MagicMock(spec=Bot)
    bot.id = 777
    bot.persona_config = {"tone": "friendly"}
    return bot


@pytest.fixture
def mock_bot_b():
    """Bot B persona fixture."""
    bot = MagicMock(spec=Bot)
    bot.id = 888
    bot.persona_config = {"tone": "formal"}
    return bot


@pytest.mark.asyncio
async def test_scope_assertion_valid():
    """Scope assertion passes with all fields present."""
    _assert_scope(bot_id=777, chat_id=123, user_id=456)
    # No exception raised


@pytest.mark.asyncio
async def test_scope_assertion_missing_bot_id():
    """Scope assertion fails if bot_id is None."""
    with pytest.raises(ScopeResolutionError, match="incomplete"):
        _assert_scope(bot_id=None, chat_id=123, user_id=456)


@pytest.mark.asyncio
async def test_scope_assertion_missing_chat_id():
    """Scope assertion fails if chat_id is None."""
    with pytest.raises(ScopeResolutionError, match="incomplete"):
        _assert_scope(bot_id=777, chat_id=None, user_id=456)


@pytest.mark.asyncio
async def test_scope_assertion_missing_user_id():
    """Scope assertion fails if user_id is None."""
    with pytest.raises(ScopeResolutionError, match="incomplete"):
        _assert_scope(bot_id=777, chat_id=123, user_id=None)


@pytest.mark.asyncio
async def test_persona_cache_isolation_same_user_two_bots(mock_bot_a, mock_bot_b):
    """Same user talking to two bots must return isolated personas."""
    user_id = 456
    chat_id = 123
    
    with patch("app.services.chat_service.bot_repo") as mock_bot_repo, \
         patch("app.services.chat_service.get_session"):
        
        # First bot lookup
        mock_bot_repo.get_by_bot_id = AsyncMock(return_value=mock_bot_a)
        persona_a = await _get_persona_cached(777)
        assert persona_a.id == 777
        assert persona_a.persona_config["tone"] == "friendly"
        
        # Second bot lookup (different bot_id)
        mock_bot_repo.get_by_bot_id = AsyncMock(return_value=mock_bot_b)
        persona_b = await _get_persona_cached(888)
        assert persona_b.id == 888
        assert persona_b.persona_config["tone"] == "formal"
        
        # Verify personas are different
        assert persona_a.id != persona_b.id
        assert persona_a.persona_config != persona_b.persona_config


@pytest.mark.asyncio
async def test_bot_resolution_failure_returns_unknown_bot_error():
    """Bot resolution failure raises UnknownBotError."""
    with patch("app.services.chat_service.bot_repo") as mock_bot_repo, \
         patch("app.services.chat_service.get_session"), \
         patch("app.services.chat_service.message_repo"), \
         patch("app.services.chat_service.relationship_repo"), \
         patch("app.services.chat_service._load_history"):
        
        mock_bot_repo.get_by_bot_id = AsyncMock(return_value=None)
        
        with pytest.raises(UnknownBotError):
            await get_reply(
                bot_id=999,
                user_id=456,
                user_message="hello",
                chat_id=123,
                dedup_key="key1",
            )


@pytest.mark.asyncio
async def test_scope_resolution_failure_on_none_chat_id():
    """Scope resolution fails if chat_id cannot be resolved."""
    with pytest.raises(ScopeResolutionError, match="incomplete"):
        await get_reply(
            bot_id=777,
            user_id=456,
            user_message="hello",
            chat_id=None,
            request_context={},  # No chat_id in context either
            dedup_key="key1",
        )


@pytest.mark.asyncio
async def test_history_retrieval_failure_raises_persistence_error():
    """History retrieval failure raises PersistenceRetryExhausted."""
    mock_bot = MagicMock(spec=Bot)
    mock_bot.id = 777
    mock_bot.persona_config = {}
    
    with patch("app.services.chat_service.bot_repo") as mock_bot_repo, \
         patch("app.services.chat_service.get_session"), \
         patch("app.services.chat_service.message_repo"), \
         patch("app.services.chat_service.relationship_repo") as mock_rel_repo, \
         patch("app.services.chat_service._load_history") as mock_load:
        
        mock_bot_repo.get_by_bot_id = AsyncMock(return_value=mock_bot)
        mock_rel_repo.ensure_relationship = AsyncMock()
        mock_load.side_effect = Exception("DB error")
        
        with pytest.raises(PersistenceRetryExhausted):
            await get_reply(
                bot_id=777,
                user_id=456,
                user_message="hello",
                chat_id=123,
                dedup_key="key1",
            )


@pytest.mark.asyncio
async def test_persona_cache_ttl_expiry(mock_bot_a):
    """Persona cache entry expires after TTL."""
    from app.services.chat_service import _persona_cache, PERSONA_CACHE_TTL_SECONDS
    _persona_cache.clear()
    
    with patch("app.services.chat_service.bot_repo") as mock_bot_repo, \
         patch("app.services.chat_service.get_session"):
        
        mock_bot_repo.get_by_bot_id = AsyncMock(return_value=mock_bot_a)
        
        # First call
        await _get_persona_cached(777)
        assert mock_bot_repo.get_by_bot_id.call_count == 1
        
        # Cache should have entry
        assert 777 in _persona_cache
        bot, inserted_at = _persona_cache[777]
        
        # Manually expire the entry by adjusting timestamp
        import time as real_time
        _persona_cache[777] = (bot, real_time.time() - (PERSONA_CACHE_TTL_SECONDS + 1))
        
        # Next call should miss cache and query DB
        await _get_persona_cached(777)
        assert mock_bot_repo.get_by_bot_id.call_count == 2
