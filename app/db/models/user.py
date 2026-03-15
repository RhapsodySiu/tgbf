from typing import Optional, List
from datetime import datetime 

from sqlalchemy import String, Integer, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    invite_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    relationships: Mapped[List["Relationship"]] = relationship(back_populates="user", cascade="all, delete-orphan")

