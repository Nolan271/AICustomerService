"""Qdrant 客户端封装 — 连接管理与集合维护"""

import logging
import time
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings

logger = logging.getLogger(__name__)


class QdrantConnectionError(Exception):
    """Qdrant 连接异常"""
    pass


class QdrantClientWrapper:
    """Qdrant 客户端包装器，管理连接与集合生命周期"""

    def __init__(self, host: str = "localhost", port: int = 6333):
        self.host = host
        self.port = port
        self.client: Optional[QdrantClient] = None
        self._connected = False
        self._connect()

    def _connect(self):
        """建立连接（带重试）"""
        try:
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                timeout=10,
                grpc_port=False,  # 仅 HTTP，避免 gRPC 额外握手开销
            )
            # 验证连接是否有效
            self.client.get_collections()
            self._connected = True
            logger.info("Qdrant 已连接: %s:%s", self.host, self.port)
        except (ConnectionRefusedError, UnexpectedResponse, Exception) as e:
            self._connected = False
            logger.warning(
                "Qdrant 未连接 (%s:%s): %s — 向量检索功能不可用，"
                "请执行 'uv run python scripts/start_qdrant.py' 启动",
                self.host, self.port, e,
            )

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def ensure_collection(self, collection: str | None = None) -> bool:
        """确保集合存在，不存在则创建"""
        if not self._connected:
            raise QdrantConnectionError(
                f"Qdrant 未连接 ({self.host}:{self.port})，"
                f"请先启动: uv run python scripts/start_qdrant.py"
            )

        collection = collection or settings.QDRANT_COLLECTION
        existing = self.client.collection_exists(collection)
        if existing:
            logger.info("Qdrant 集合 '%s' 已存在", collection)
            return True

        logger.info("创建 Qdrant 集合 '%s' (size=%d) ...", collection, settings.QDRANT_VECTOR_SIZE)
        self.client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=settings.QDRANT_VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Qdrant 集合 '%s' 创建完成", collection)
        return True

    async def upsert(self, points: list[dict], collection: str | None = None):
        """批量写入向量点"""
        if not self._connected:
            raise QdrantConnectionError("Qdrant 未连接，无法写入")
        collection = collection or settings.QDRANT_COLLECTION
        self.client.upsert(collection_name=collection, points=points)

    async def delete_points(self, point_ids: list[str], collection: str | None = None):
        if not self._connected:
            return
        collection = collection or settings.QDRANT_COLLECTION
        self.client.delete(collection_name=collection, points_selector=point_ids)

    async def delete_by_filter(self, key: str, value: str, collection: str | None = None):
        if not self._connected:
            return
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        collection = collection or settings.QDRANT_COLLECTION
        self.client.delete(
            collection_name=collection,
            points_selector=Filter(
                must=[FieldCondition(key=key, match=MatchValue(value=value))]
            ),
        )

    async def count(self, collection: str | None = None) -> int:
        if not self._connected:
            return 0
        collection = collection or settings.QDRANT_COLLECTION
        result = self.client.count(collection_name=collection)
        return result.count

    def close(self):
        if self.client:
            self.client.close()
            self._connected = False
