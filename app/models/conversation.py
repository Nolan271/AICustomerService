"""SQLAlchemy ORM 模型 — 对话会话"""

import datetime
from typing import Optional

from sqlalchemy import String, Text, Enum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import Base
from app.utils.common import generate_uuid


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    kb_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("knowledge_bases.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), default="新对话")
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.ACTIVE
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关系
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")
