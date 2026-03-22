from app.llm.adapter import llm
from app.llm.prompts import build_system_prompt

# temporary in-memory history per user (dict keyed by user_id)
# TODO: replaced by DB
_histories: dict[int, list[dict]] = {}

HISTORY_MAX_SIZE = 20

async def get_reply(user_id: int, user_message: str) -> str:
    histories = _histories.get(user_id)
    
    if histories is None:
        histories = []
    
    histories.append({
        "role": "user",
        "content": user_message,
    })

    messages = [{
        "role": "system",
        "content": build_system_prompt("", {}), # TODO: get bot info
    }, *histories]

    reply = await llm.chat(messages)

    histories.append({"role": "assistant", "content": reply})

    _histories[user_id] = histories[-HISTORY_MAX_SIZE:]

    return reply


