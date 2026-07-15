"""Embedding 服务 — 统一封装多种 Embedding 后端

支持:
  - openai:     OpenAI 兼容接口（适合阿里云百炼 OpenAI 兼容模式）
                → model 参数传 qwen3-vl-rerank 等
  - dashscope:  阿里云 DashScope SDK（推荐，支持 text-embedding-v3）
  - ollama:     本地 Ollama 嵌入模型
"""

import logging
from typing import Optional

from langchain_openai import OpenAIEmbeddings
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding 服务 — 支持 OpenAI 兼容、DashScope、Ollama"""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.model = model or settings.EMBEDDING_MODEL
        self._embeddings = self._build_client()
        logger.info(
            "Embedding 初始化: provider=%s, model=%s",
            self.provider, self.model,
        )

    def _build_client(self):
        if self.provider == "openai":
            # OpenAI 兼容接口（适合阿里云百炼 OpenAI 兼容模式）
            # 通过 OPENAI_BASE_URL + OPENAI_API_KEY 指向阿里云百炼
            return OpenAIEmbeddings(
                model=self.model,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )

        elif self.provider == "dashscope":
            # 阿里云 DashScope SDK（原生接口，推荐）
            # 注意: DashScopeEmbeddings 通过 dashscope 包 SDK 连接，
            # 自定义 endpoint 通过环境变量 DASHSCOPE_API_BASE 或全局设置
            import dashscope
            api_key = settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
            if settings.DASHSCOPE_BASE_URL:
                dashscope.base_http_api_url = settings.DASHSCOPE_BASE_URL

            from langchain_community.embeddings import DashScopeEmbeddings
            return DashScopeEmbeddings(
                model=self.model,
                dashscope_api_key=api_key,
            )

        elif self.provider == "ollama":
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                model=self.model,
                base_url=settings.OLLAMA_BASE_URL,
            )

        else:
            raise ValueError(
                f"不支持的 Embedding 提供商: {self.provider}，"
                f"可选: openai (百炼兼容), dashscope (百炼原生), ollama"
            )

    async def aembed_query(self, text: str) -> list[float]:
        """异步：单条文本 → 向量"""
        try:
            return await self._embeddings.aembed_query(text)
        except Exception as e:
            logger.error("Embedding 查询失败: %s", e)
            raise

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """异步：批量文本 → 向量"""
        try:
            return await self._embeddings.aembed_documents(texts)
        except Exception as e:
            logger.error("Embedding 批量处理失败 (len=%d): %s", len(texts), e)
            raise

    def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)
