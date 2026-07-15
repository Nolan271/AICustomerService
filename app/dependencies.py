"""FastAPI 依赖注入 — 统一管理各服务的创建与生命周期"""

from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import async_session_factory
from app.qdrant.client import QdrantClientWrapper
from app.qdrant.search import QdrantSearcher
from app.rag.embedder import EmbeddingService
from app.rag.retriever import RAGRetriever
from app.rag.ingestion import IngestionPipeline
from app.llm.factory import LLMFactory
from app.core.chat_service import ChatService
from app.core.kb_service import KBService


# ── Qdrant 客户端（单例） ──────────────────────────────────────────
_qdrant_client: Optional[QdrantClientWrapper] = None


def get_qdrant_client() -> QdrantClientWrapper:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClientWrapper(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
    return _qdrant_client


# ── Embedding 服务（单例） ─────────────────────────────────────────
_embedder: Optional[EmbeddingService] = None


def get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService()
    return _embedder


# ── RAG 检索器 ─────────────────────────────────────────────────────
def get_retriever() -> RAGRetriever:
    return RAGRetriever(
        embedder=get_embedder(),
        qdrant_searcher=QdrantSearcher(
            client=get_qdrant_client().client,
            collection=settings.QDRANT_COLLECTION,
        ),
        top_k=settings.TOP_K_RETRIEVAL,
        score_threshold=settings.RETRIEVAL_SCORE_THRESHOLD,
    )


# ── 摄入流水线 ──────────────────────────────────────────────────────
def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        embedder=get_embedder(),
        qdrant=get_qdrant_client(),
    )


# ── 数据库 Session（请求级） ────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ── ChatService ─────────────────────────────────────────────────────
async def get_chat_service() -> ChatService:
    return ChatService(
        retriever=get_retriever(),
        embedder=get_embedder(),
    )


# ── KBService ───────────────────────────────────────────────────────
async def get_kb_service(
    session=Depends(get_db),
) -> KBService:
    return KBService(
        db=session,
        ingestion=get_ingestion_pipeline(),
    )
