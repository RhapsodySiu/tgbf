#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
from typing import Optional

from app.db.models.bot import Bot
from app.db.repositories.bot import BotRepository
from app.db.session import get_session


def load_persona_config(value: Optional[str]) -> Optional[dict]:
    if not value:
        return None
    # If it points to an existing file, read it
    if os.path.exists(value):
        with open(value, "r", encoding="utf-8") as f:
            return json.load(f)
    # Otherwise treat as JSON text
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise ValueError("`--persona-config` must be a valid file path or JSON string")


async def main():
    parser = argparse.ArgumentParser(description="Insert or update a bot")
    parser.add_argument("--bot-id", type=str, required=True, help="Bot id (primary key)")
    parser.add_argument("--display-name", type=str, default=None)
    parser.add_argument("--telegram-token", type=str, default=None, help="Telegram bot token")
    parser.add_argument("--persona-config", type=str, default=None, help="Path to JSON file or raw JSON text")
    parser.add_argument("--activate", dest="is_active", action="store_true")
    parser.add_argument("--deactivate", dest="is_active", action="store_false")
    parser.set_defaults(is_active=None)

    args = parser.parse_args()

    persona = None
    if args.persona_config:
        persona = load_persona_config(args.persona_config)

    repo = BotRepository(Bot)

    payload = {}
    if args.display_name is not None:
        payload["display_name"] = args.display_name
    if args.telegram_token is not None:
        payload["telegram_token"] = args.telegram_token
    if persona is not None:
        payload["persona_config"] = persona
    if args.is_active is not None:
        payload["is_active"] = args.is_active

    async with get_session() as session:
        existing = await repo.get_by_id(session, args.bot_id)
        if existing:
            if not payload:
                print("No fields to update; exiting.")
                return
            bot = await repo.update(session, args.bot_id, payload)
            action = "updated"
        else:
            # ensure required fields for creation
            create_payload = {"bot_id": args.bot_id}
            create_payload.update(payload)
            bot = await repo.create(session, create_payload)
            action = "created"

    print(f"Bot {action}: bot_id={bot.bot_id}, display_name={bot.display_name}, is_active={bot.is_active}")
    

if __name__ == "__main__":
    asyncio.run(main())