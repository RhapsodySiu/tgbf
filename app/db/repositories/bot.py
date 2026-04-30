from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.models.bot import Bot
from app.db.repositories.base import CRUDRepository


class BotRepository(CRUDRepository[Bot, int]):
    async def get_by_bot_id(self, db: AsyncSession, bot_id: str) -> Optional[Bot]:
        return await self.get_by_id(db, bot_id)

    async def set_persona_config(self, db: AsyncSession, bot_id: str, persona_config: dict):
        return await self.update(db, bot_id, {"persona_config": persona_config})