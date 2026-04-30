from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.db.models.message import Message, Direction, ContentType
from app.services.log_context import get_log_context

from app.db.repositories.base import CRUDRepository
from app.db.models.message import Message


logger = logging.getLogger(__name__)


class ChatMessageRepository(CRUDRepository[Message, str]):
    async def save_inbound(
        self,
        db: AsyncSession,
        bot_id: str,
        chat_id: int,
        user_id: int,
        content: str,
        metadata: Optional[dict] = None,
        dedup_key: Optional[str] = None,
    ) -> Message:
        if dedup_key:
            existing_stmt = select(Message).where(
                Message.bot_id == bot_id,
                Message.chat_id == chat_id,
                Message.user_id == user_id,
                Message.direction == Direction.INBOUND,
                Message.dedup_key == dedup_key,
            )
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()
            if existing is not None:
                logger.info(
                    "duplicate_inbound_skipped",
                    extra={"dedup_key": dedup_key, **get_log_context()},
                )
                return existing

        return await self.create(db, {
            "message_id": str(uuid4()),
            "bot_id": bot_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "dedup_key": dedup_key,
            "direction": Direction.INBOUND,
            "content_type": ContentType.TEXT,
            "content": content,
            "attachment_path": None,
            "metadata_": metadata or {},
        })

    async def save_outbound(
        self,
        db: AsyncSession,
        bot_id: str,
        chat_id: int,
        user_id: int,
        content: str,
        metadata: Optional[dict] = None,
    ) -> Message:
        return await self.create(db, {
            "message_id": str(uuid4()),
            "bot_id": bot_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "dedup_key": None,
            "direction": Direction.OUTBOUND,
            "content_type": ContentType.TEXT,
            "content": content,
            "attachment_path": None,
            "metadata_": metadata or {},
        })

    async def get_recent_for_context(
        self,
        db: AsyncSession,
        bot_id: str,
        chat_id: int,
        user_id: int,
        limit: int = 20,
    ) -> List[Message]:
        stmt = (
            select(Message)
            .where(
                Message.bot_id == bot_id,
                Message.chat_id == chat_id,
                Message.user_id == user_id,
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows


    async def get_before_timestamp(
        self,
        db: AsyncSession,
        bot_id: str,
        chat_id: int,
        user_id: int,
        cursor: datetime,
        limit: int,
    ) -> List[Message]:
        stmt = (
            select(Message)
            .where(
                Message.bot_id == bot_id,
                Message.chat_id == chat_id,
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