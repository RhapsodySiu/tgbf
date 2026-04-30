from aiogram import Router, F
from aiogram.types import Message

from app.services.chat_service import (
    PersistenceRetryExhausted,
    ScopeResolutionError,
    UnknownBotError,
    get_reply,
)
from app.services.log_context import bind_log_context, clear_log_context

router = Router()

@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id if message.chat else None
    bot_id = str(message.bot.id)
    dedup_key = str(message.message_id) if message.message_id is not None else None

    bind_log_context(bot_id=bot_id, chat_id=chat_id, user_id=user_id)
    try:
        reply = await get_reply(
            bot_id=bot_id,
            user_id=user_id,
            user_message=message.text or "",
            chat_id=chat_id,
            dedup_key=dedup_key,
            request_context={"chat_id": chat_id},
        )
        await message.answer(reply, parse_mode=None)
    except ScopeResolutionError:
        await message.answer("Unable to resolve chat scope. Please try again.", parse_mode=None)
    except UnknownBotError:
        await message.answer("Bot configuration not found. Please contact support.", parse_mode=None)
    except PersistenceRetryExhausted:
        await message.answer("Temporary storage issue. Please try again shortly.", parse_mode=None)
    finally:
        clear_log_context()