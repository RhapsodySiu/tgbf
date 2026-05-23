import logging
import asyncio
from time import time
from typing import Tuple

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.db.session import get_session

logger = logging.getLogger(__name__)

# Rate limiter state: {(bot_id, user_id, minute): count}
_quota_counters: dict[Tuple[int, int, int], int] = {}
_quota_lock = asyncio.Lock()

QUOTA_PER_BOT_USER_PER_MINUTE = 100


class AllowlistMiddleware(BaseMiddleware):
    def __init__(self):
        self.user_repo = UserRepository(User)
        super().__init__()

    async def __call__(self, handler, event, data):
        sender = data.get("event_from_user")
        if not sender:
            return await handler(event, data)

        # Extract bot_id and check rate limit first (before allowlist).
        if isinstance(event, Message) and event.bot and event.bot.id:
            bot_id = event.bot.id
            user_id = sender.id
            
            # Check rate limit
            if not await self._check_quota(bot_id, user_id):
                logger.warning("rate_limit_rejected", extra={"bot_id": bot_id, "user_id": user_id})
                if isinstance(event, Message):
                    await event.answer("You're sending messages too quickly. Please try again in a moment.", parse_mode=None)
                return

        # Let onboarding entrypoint pass through for unregistered users.
        if isinstance(event, Message) and isinstance(event.text, str) and event.text.startswith("/start"):
            return await handler(event, data)
        
        try:
            async with get_session() as session:
                user = await self.user_repo.get_by_id(session, sender.id)
                if user and user.is_allowed:
                    return await handler(event, data)

                logger.info("allowlist.denied", extra={"user_id": sender.id})
                if isinstance(event, Message):
                    await event.answer("Access denied. Please complete onboarding with /start <invite_token>.", parse_mode=None)
                return
        except Exception:
            logger.exception("allowlist.db_error", extra={"user_id": sender.id})
            if isinstance(event, Message):
                await event.answer("Service temporarily unavailable. Please try again.", parse_mode=None)
            return

    async def _check_quota(self, bot_id: int, user_id: int) -> bool:
        """Check and increment quota counter for (bot_id, user_id) in current minute."""
        current_minute = int(time() // 60)
        quota_key = (bot_id, user_id, current_minute)
        
        async with _quota_lock:
            # Clean up old minute counters
            current_keys = list(_quota_counters.keys())
            for key in current_keys:
                if key[2] < current_minute - 1:
                    del _quota_counters[key]
            
            # Check and increment counter
            current_count = _quota_counters.get(quota_key, 0)
            if current_count >= QUOTA_PER_BOT_USER_PER_MINUTE:
                return False
            
            _quota_counters[quota_key] = current_count + 1
            return True