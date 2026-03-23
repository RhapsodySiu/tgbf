import asyncio
import logging
import os

import app.db.models

from fastapi import FastAPI
from app.bot import bot, dp
from app.handlers.commands import router as command_router
from app.handlers.messages import router as message_router
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError

from app.config import settings
from app.middlewares.allowlist import AllowlistMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Main")

dp.message.middleware(AllowlistMiddleware())
dp.include_routers(command_router, message_router)

# placeholder web server
app = FastAPI()

@app.get("/")
def index():
    return "Hello World"

@app.get("/persona/{id}")
def getPersona(id:str):
    return {"data": "Person:" + id}

async def main():
    if settings.app_mode == "polling":
        logger.info("Server running")
        try:
            await bot.delete_webhook(drop_pending_updates=True)

            await dp.start_polling(bot)
        except TelegramBadRequest as e:
            logger.error(f"Telegram API error: {e}")
        except TelegramUnauthorizedError as e:
            logger.error(f"Telegram unauthorized: {e}")
        except asyncio.exceptions.CancelledError as e:
            logger.info("Server interrupted")
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
        finally:
            await bot.session.close()
            logger.info("Bot stopped")
    elif settings.app_mode == "webhook":
        print("WEBHOOK")


if __name__ == "__main__":
    asyncio.run(main())