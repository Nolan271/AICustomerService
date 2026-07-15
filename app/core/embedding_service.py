"""核心业务 — Embedding 服务封装

复用 app/rag/embedder.py，此为业务层适配。
"""

from app.rag.embedder import EmbeddingService as RagEmbeddingService


class EmbeddingService(RagEmbeddingService):
    """业务层 Embedding 服务（继承 RAG 层实现）"""
    pass
