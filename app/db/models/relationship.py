from typing import Optional
from datetime import datetime

from sqlalchemy import String, ForeignKey, JSON, Integer, PrimaryKeyConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Relationship(Base):
    __tablename__ = "relationships"

    bot_id: Mapped[str] = mapped_column(ForeignKey("bots.bot_id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)

    relationship_state: Mapped[dict] = mapped_column(JSON)
    user_preferences: Mapped[dict] = mapped_column(JSON)
    last_interaction: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bot: Mapped["Bot"] = relationship(back_populates="relationships")
    user: Mapped["User"] = relationship(back_populates="relationships")

    __table_args__ = (
        PrimaryKeyConstraint("bot_id", "user_id", name="pk_bot_user"),
    )