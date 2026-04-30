from typing import Optional
from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, Enum as SqlEnum, Text, String, JSON, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Direction(Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class ContentType(Enum):
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    STICKER = "sticker"

class Message(Base):
    __tablename__ = "message"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    bot_id: Mapped[str] = mapped_column(ForeignKey("bots.bot_id"), nullable=False)
    chat_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    dedup_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    direction: Mapped[Direction] = mapped_column(SqlEnum(Direction), nullable=False)
    content_type: Mapped[ContentType] = mapped_column(SqlEnum(ContentType), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
