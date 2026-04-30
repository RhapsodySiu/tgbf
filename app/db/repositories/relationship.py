from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.relationship import Relationship
from app.db.repositories.base import CRUDRepository


class RelationshipRepository(CRUDRepository[Relationship, int]):
    async def get_relationship(self, db: AsyncSession, bot_id: str, user_id: int) -> Relationship | None:
        stmt = select(Relationship).where(
            Relationship.bot_id == bot_id,
            Relationship.user_id == user_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def ensure_relationship(self, db: AsyncSession, bot_id: str, user_id: int) -> Relationship:
        existing = await self.get_relationship(db, bot_id, user_id)
        if existing is not None:
            return existing

        return await self.create(
            db,
            {
                "bot_id": bot_id,
                "user_id": user_id,
                "relationship_state": {},
                "user_preferences": {},
            },
        )