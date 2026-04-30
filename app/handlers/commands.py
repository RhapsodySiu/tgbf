import logging
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.db.session import get_session

router = Router()
logger = logging.getLogger(__name__)
user_repo = UserRepository(User)

INVALID_INVITE_MESSAGE = "Sorry, that invite link isn't valid. Please check your link."
GENERIC_FAILURE_MESSAGE = "Something went wrong. Please try again later."
NO_TOKEN_WELCOME_MESSAGE = "Welcome! Please send /start <invite_token> to complete onboarding."


def _extract_token(text: str | None) -> str | None:
    if not text:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    token = parts[1].strip()
    return token or None

@router.message(Command("start"))
async def cmd_start(message: Message):
    sender = message.from_user
    if sender is None:
        await message.answer(GENERIC_FAILURE_MESSAGE, parse_mode=None)
        return

    token = _extract_token(message.text)
    if token is None:
        await message.answer(NO_TOKEN_WELCOME_MESSAGE, parse_mode=None)
        return

    try:
        async with get_session() as session:
            user = await user_repo.get_by_invite_token(session, token)
            if user is None:
                logger.warning("onboarding.invalid_token", extra={"user_id": sender.id})
                await message.answer(INVALID_INVITE_MESSAGE, parse_mode=None)
                return

            if user.user_id != sender.id:
                logger.warning("onboarding.user_id_mismatch", extra={"user_id": sender.id})
                await message.answer(INVALID_INVITE_MESSAGE, parse_mode=None)
                return

            update_payload = {
                "username": sender.username,
                "first_name": sender.first_name,
            }
            if user.joined_at is None:
                update_payload["joined_at"] = datetime.utcnow()
            if not user.is_allowed:
                update_payload["is_allowed"] = True

            await user_repo.update(session, user.user_id, update_payload)

            first_name = sender.first_name or "there"
            if user.is_allowed:
                success_message = f"Welcome back, {first_name}! You're all set."
            else:
                success_message = f"Welcome, {first_name}! You can now chat."

            logger.info("onboarding.success", extra={"user_id": sender.id})
            await message.answer(success_message, parse_mode=None)
    except Exception:
        logger.exception("onboarding.db_error", extra={"user_id": sender.id})
        await message.answer(GENERIC_FAILURE_MESSAGE, parse_mode=None)