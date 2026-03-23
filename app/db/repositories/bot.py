from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.bot import Bot
from app.db.repositories.base import CRUDRepository


class BotRepository(CRUDRepository[Bot, int]):
    async def set_persona_config(self, db: AsyncSession, bot_id: str, persona_config: dict):
        result = await self.update(self, db, bot_id, { "persona_config": persona_config })