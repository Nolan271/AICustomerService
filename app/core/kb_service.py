"""核心业务 — 知识库服务

管理知识库的 CRUD 和文档摄入流程。
"""

import logging
import os
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document, DocumentStatus
from app.rag.ingestion import IngestionPipeline

logger = logging.getLogger(__name__)


class KBService:
    """知识库服务"""

    def __init__(self, db: AsyncSession, ingestion: IngestionPipeline):
        self.db = db
        self.ingestion = ingestion

    # ── 知识库 CRUD ──────────────────────────────────────────────

    async def create_kb(self, name: str, description: Optional[str] = None) -> KnowledgeBase:
        kb = KnowledgeBase(name=name, description=description)
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        logger.info("知识库创建: id=%s, name=%s", kb.id, name)
        return kb

    async def get_kb(self, kb_id: str) -> Optional[KnowledgeBase]:
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        return result.scalar_one_or_none()

    async def list_kbs(self) -> list[KnowledgeBase]:
        result = await self.db.execute(
            select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_kb(self, kb_id: str, data: dict) -> Optional[KnowledgeBase]:
        kb = await self.get_kb(kb_id)
        if not kb:
            return None
        for key, value in data.items():
            if value is not None and hasattr(kb, key):
                setattr(kb, key, value)
        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def delete_kb(self, kb_id: str) -> bool:
        kb = await self.get_kb(kb_id)
        if not kb:
            return False
        await self.db.delete(kb)
        await self.db.commit()
        return True

    # ── 文档管理 ─────────────────────────────────────────────────

    async def save_upload(self, content: bytes, filename: str, kb_id: str) -> str:
        """保存上传文件到磁盘"""
        upload_dir = Path(settings.UPLOAD_DIR) / kb_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename
        file_path.write_bytes(content)
        return str(file_path)

    async def ingest_document(
        self,
        kb_id: str,
        file_path: str,
        file_type: str,
        original_filename: str,
    ) -> Document:
        """摄入文档：创建记录 → 执行流水线 → 更新状态"""
        doc = Document(
            kb_id=kb_id,
            filename=original_filename,
            file_type=file_type,
            file_size=os.path.getsize(file_path),
            status=DocumentStatus.PROCESSING,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        try:
            chunk_count = await self.ingestion.ingest(
                file_path=file_path,
                file_type=file_type,
                kb_id=kb_id,
                doc_id=doc.id,
                doc_name=original_filename,
            )
            doc.status = DocumentStatus.READY
            doc.chunk_count = chunk_count
        except Exception as e:
            logger.exception("文档摄入失败: doc=%s", doc.id)
            doc.status = DocumentStatus.FAILED

        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def list_documents(self, kb_id: str) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.kb_id == kb_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_document(self, doc_id: str) -> bool:
        from sqlalchemy import select
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False
        await self.db.delete(doc)
        await self.db.commit()
        return True
