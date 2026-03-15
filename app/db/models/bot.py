from typing import Optional, List
from datetime import datetime 

from sqlalchemy import String, Integer, Boolean, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import EncryptedType
from app.db.base import Base
from app.config import settings

class Bot(Base):
    __tablename__ = "bots"

    bot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    telegram_token: Mapped[str] = mapped_column(EncryptedType(String, settings.encryption_key), nullable=False)
    persona_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    relationships: Mapped[List["Relationship"]] = relationship(back_populates="bot", cascade="all, delete-orphan")

