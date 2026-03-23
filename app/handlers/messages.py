from aiogram import Router, F
from aiogram.types import Message

from app.services.chat_service import get_reply

router = Router()

@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    reply = await get_reply(user_id, message.text)
    await message.answer(reply, parse_mode=None)