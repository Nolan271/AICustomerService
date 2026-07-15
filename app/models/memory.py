"""SQLAlchemy ORM 模型 — 记忆模块

三层记忆体系:
  short_term  → 当前对话上下文 (messages 表)
  long_term   → 从对话中提取的重要事实
  preference  → 用户偏好设置
"""

import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.common import generate_uuid


class MemoryFact(Base):
    """长期记忆 — 从对话中提取的事实性信息"""

    __tablename__ = "memory_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="用户标识"
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="来源会话 ID"
    )
    fact_type: Mapped[str] = mapped_column(
        String(50), default="general", comment="事实类型: general | product | requirement | preference"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="记忆内容"
    )
    keywords: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="关键词，逗号分隔"
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=0.5, comment="置信度 0-1"
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="来源: user_stated | ai_inferred | system"
    )
    access_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_accessed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_memory_user_type", "user_id", "fact_type"),
    )


class UserPreference(Base):
    """偏好记忆 — 用户个性化设置"""

    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="用户标识"
    )
    pref_key: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="偏好键"
    )
    pref_value: Mapped[str] = mapped_column(
        Text, nullable=False, comment="偏好值 (JSON)"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_pref_user_key", "user_id", "pref_key", unique=True),
    )
