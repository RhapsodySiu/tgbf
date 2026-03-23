from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.message import Message, Direction, ContentType

from app.db.repositories.base import CRUDRepository
from app.db.models.message import Message

class ChatMessageRepository(CRUDRepository[Message, str]):
    async def save_inbound(self, db: AsyncSession, bot_id: str, user_id: int, content: str, metadata: Optional[dict] = None) -> Message:
        return await self.create(db, {
            "message_id": str(uuid4()),
            "bot_id": bot_id,
            "user_id": user_id,
            "direction": Direction.INBOUND,
            "content_type": ContentType.TEXT,
            "content": content,
            "attachment_path": None,
            "metadata_": metadata or {},
        })

    async def save_outbound(self, db: AsyncSession, bot_id: str, user_id: int, content: str, metadata: Optional[dict] = None) -> Message:
        return await self.create(db, {
            "message_id": str(uuid4()),
            "bot_id": bot_id,
            "user_id": user_id,
            "direction": Direction.OUTBOUND,
            "content_type": ContentType.TEXT,
            "content": content,
            "attachment_path": None,
            "metadata_": metadata or {},
        })

    async def get_recent_for_context(self, db: AsyncSession, bot_id: str, user_id: int, limit: int) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.bot_id == bot_id, Message.user_id == user_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows


    async def get_before_timestamp(self, db: AsyncSession, bot_id: str, user_id: int, cursor: datetime, limit: int) -> List[Message]:
        stmt = (
            select(Message)
            .where(
                Message.bot_id == bot_id,
                Message.user_id == user_id,
                Message.created_at < cursor,
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows