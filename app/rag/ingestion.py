"""知识库摄入流水线 — 文档解析 → 分块 → 向量化 → 存储"""

import logging
import uuid
from typing import Optional

from langchain_core.documents import Document as LCDocument

from app.config import settings
from app.rag.embedder import EmbeddingService
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.qdrant.client import QdrantClientWrapper

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """文档摄入流水线

    Usage:
        pipeline = IngestionPipeline(embedder, qdrant)
        chunk_count = await pipeline.ingest("path/to/doc.pdf", "pdf", kb_id, doc_id)
    """

    def __init__(self, embedder: EmbeddingService, qdrant: QdrantClientWrapper):
        self.embedder = embedder
        self.qdrant = qdrant

    async def ingest(
        self,
        file_path: str,
        file_type: str,
        kb_id: str,
        doc_id: str,
        doc_name: str = "",
        metadata: Optional[dict] = None,
    ) -> int:
        """摄入单个文档

        Returns:
            分块数量
        """
        # 1. 加载文档
        logger.info("加载文档: %s (type=%s)", file_path, file_type)
        documents: list[LCDocument] = load_document(file_path, file_type)
        logger.info("文档加载完成: %d 页/段", len(documents))

        # 2. 分块
        chunks = split_documents(documents)
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "doc_id": doc_id,
                "kb_id": kb_id,
                "chunk_index": i,
                "doc_name": doc_name or file_path.split("/")[-1],
                **(metadata or {}),
            })
        logger.info("分块完成: %d 个块", len(chunks))

        if not chunks:
            return 0

        # 3. 批量向量化并写入 Qdrant
        BATCH_SIZE = 20
        total_points = 0

        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            texts = [c.page_content for c in batch]
            vectors = await self.embedder.aembed_documents(texts)

            points = [
                {
                    "id": str(uuid.uuid4()),
                    "vector": vectors[j],
                    "payload": {
                        "text": batch[j].page_content,
                        **batch[j].metadata,
                    },
                }
                for j in range(len(batch))
            ]

            await self.qdrant.upsert(points)
            total_points += len(points)

        logger.info("摄入完成: doc=%s, chunks=%d, points=%d", doc_id, len(chunks), total_points)
        return len(chunks)
