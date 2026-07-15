"""SQLAlchemy ORM 模型 — MinerU 解析产出的非向量资产（图片、表格）"""

import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.common import generate_uuid


class DocumentImage(Base):
    """文档中的图片 — MinerU 提取，不适合直接向量化，存引用"""

    __tablename__ = "document_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    doc_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="MinerU 文档 UUID"
    )
    kb_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id"), nullable=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="原始 PDF 文件名"
    )
    image_filename: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="图片文件名 (UUID.jpg)"
    )
    image_path: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="图片完整路径"
    )
    alt_text: Mapped[str] = mapped_column(
        Text, default="", comment="图片说明/上下文"
    )
    page_index: Mapped[int] = mapped_column(
        Integer, default=0, comment="所在页码"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="图片文件大小(bytes)"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DocumentTable(Base):
    """文档中的表格 — MinerU 提取，渲染为图片，存引用"""

    __tablename__ = "document_tables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    doc_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="MinerU 文档 UUID"
    )
    kb_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id"), nullable=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="原始 PDF 文件名"
    )
    image_path: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="表格渲染图路径"
    )
    caption: Mapped[str] = mapped_column(
        Text, default="", comment="表格标题"
    )
    page_index: Mapped[int] = mapped_column(
        Integer, default=0, comment="所在页码"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
