"""Qdrant 搜索封装 — 向量检索（qdrant-client v1.18+ API）"""

from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
)

from app.config import settings


class QdrantSearcher:
    """Qdrant 向量检索器"""

    def __init__(self, client: QdrantClient, collection: str):
        self.client = client
        self.collection = collection

    async def search(
        self,
        query_vector: list[float],
        query_text: str | None = None,
        collection: str | None = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
        kb_id: str | None = None,
        extra_filters: dict | None = None,
    ) -> list:
        """向量检索：query_vector → Qdrant query_points

        新版 qdrant-client 使用 query_points() 替代 search()。
        返回 list of ScoredPoint。
        """
        coll = collection or self.collection
        filters = self._build_filter(kb_id, extra_filters)

        response = self.client.query_points(
            collection_name=coll,
            query=query_vector,
            query_filter=filters,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )

        # query_points 返回 QueryResponse，.points 是 ScoredPoint 列表
        return response.points

    def _build_filter(
        self,
        kb_id: str | None,
        extra: dict | None,
    ) -> Filter | None:
        must_conditions = []
        if kb_id:
            must_conditions.append(
                FieldCondition(key="kb_id", match=MatchValue(value=kb_id))
            )
        if extra:
            for key, value in extra.items():
                must_conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value),
                    )
                )
        return Filter(must=must_conditions) if must_conditions else None
