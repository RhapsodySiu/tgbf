from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import CRUDRepository
from app.db.models.user import User

class UserRepository(CRUDRepository[User, int]):
    async def get_by_invite_token(self, db: AsyncSession, token: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.invite_token == token)            
        )

        return result.scalar_one_or_none()

    async def get_allowed_users(self, db: AsyncSession) -> list[User]:
        result = await db.execute(
            select(User).where(User.is_allowed.is_(True))
        )
        return list(result.scalars().all())

    async def set_allowed(self, db: AsyncSession, user_id: int, allowed: bool) -> User:
        return await self.update(db, user_id, {"is_allowed": allowed})
