"""检索器 — RAG 在线检索流水线"""

import logging
from typing import Optional

from app.config import settings
from app.rag.embedder import EmbeddingService
from app.qdrant.search import QdrantSearcher
from app.rag.reranker import RerankerService

logger = logging.getLogger(__name__)


class RAGRetriever:
    """RAG 检索器：embedding → 混合搜索 → 可选重排序"""

    def __init__(
        self,
        embedder: EmbeddingService,
        qdrant_searcher: QdrantSearcher,
        reranker: Optional[RerankerService] = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ):
        self.embedder = embedder
        self.searcher = qdrant_searcher
        self.reranker = reranker
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def retrieve(
        self,
        query: str,
        kb_id: str | None = None,
        filters: dict | None = None,
    ) -> list[dict]:
        """完整检索流程

        Args:
            query: 用户问题
            kb_id: 知识库 ID（可选，用于过滤）
            filters: 额外元数据过滤条件

        Returns:
            检索结果列表，每项包含 text, score, metadata 等
        """
        # 1. 问题向量化
        query_vector = await self.embedder.aembed_query(query)

        # 2. Qdrant 混合搜索
        results = await self.searcher.search(
            query_vector=query_vector,
            query_text=query,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            kb_id=kb_id,
            extra_filters=filters,
        )

        # 3. 格式化结果
        formatted = []
        for r in results:
            payload = r.payload or {}
            formatted.append({
                "id": r.id,
                "score": r.score,
                "text": payload.get("text", ""),
                "doc_id": payload.get("doc_id"),
                "kb_id": payload.get("kb_id"),
                "chunk_index": payload.get("chunk_index"),
                "doc_name": payload.get("doc_name", ""),
                "metadata": {
                    k: v for k, v in payload.items()
                    if k not in ("text", "doc_id", "kb_id", "chunk_index", "doc_name")
                },
            })

        # 4. 可选重排序
        if self.reranker and len(formatted) > 1:
            formatted = await self.reranker.rerank(
                query=query,
                documents=formatted,
                top_k=min(self.top_k, settings.TOP_K_RERANK),
            )

        logger.info("检索完成: query='%s', 结果数=%d", query[:50], len(formatted))
        return formatted
