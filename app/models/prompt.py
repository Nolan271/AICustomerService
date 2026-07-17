"""SQLAlchemy ORM 模型 — 提示词"""

import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.common import generate_uuid


class PromptItem(Base):
    """提示词"""
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment="分类: revenue/orders/device")
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="提示词文本")
    intent: Mapped[str] = mapped_column(String(20), nullable=False, comment="意图: DATA_QUERY/KB_QA")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
