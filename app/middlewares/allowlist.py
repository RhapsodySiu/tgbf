import logging

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.db.session import get_session

logger = logging.getLogger(__name__)


class AllowlistMiddleware(BaseMiddleware):
    def __init__(self):
        self.user_repo = UserRepository(User)
        super().__init__()

    async def __call__(self, handler, event, data):
        sender = data.get("event_from_user")
        if not sender:
            return await handler(event, data)

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