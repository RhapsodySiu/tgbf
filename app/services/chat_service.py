from app.db.models.bot import Bot
from app.db.models.message import Message
from app.db.repositories.bot import BotRepository
from app.db.repositories.message import ChatMessageRepository
from app.db.session import get_session
from app.llm.adapter import llm
from app.llm.prompts import build_system_prompt

# temporary in-memory history per user (dict keyed by user_id)
# TODO: replaced by DB
_histories: dict[int, list[dict]] = {}

# TODO: better cache implementation
repo = BotRepository(Bot)
message_repo = ChatMessageRepository(Message)
_bot_data = None
BOT_ID = str(8239967866)

HISTORY_MAX_SIZE = 20

async def fetch_bot_data() -> dict:
    global _bot_data
    if _bot_data is None:
        print("Miss bot_data cache, fetching...")
        async with get_session() as session:
            existing = await repo.get_by_id(session, BOT_ID)
            if existing is None:
                raise Exception("Persona data not found for hardcoded bot")
            
            _bot_data = existing.persona_config
    return _bot_data

async def get_reply(user_id: int, user_message: str) -> str:
    histories = _histories.get(user_id)
    
    if histories is None:
        histories = []
    
    histories.append({
        "role": "user",
        "content": user_message,
    })

    persona = await fetch_bot_data()

    # persist inbound message
    async with get_session() as session:
        
        await message_repo.save_inbound(session, BOT_ID, user_id, user_message)

    messages = [{
        "role": "system",
        "content": build_system_prompt("Test", persona),
    }, *histories]

    reply = await llm.chat(messages)

    # persist outbound message
    async with get_session() as session:
        await message_repo.save_outbound(session, BOT_ID, user_id, reply) 

    histories.append({"role": "assistant", "content": reply})

    _histories[user_id] = histories[-HISTORY_MAX_SIZE:]

    return reply


