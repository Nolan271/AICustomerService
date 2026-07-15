"""重排序服务 — 对检索结果进行精排，提高 Top-K 准确率

使用阿里云百炼 qwen3-vl-rerank 模型进行语义级精排。
"""

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class RerankerService:
    """检索结果重排序

    通过阿里云百炼的 DashScope TextReRank API 对检索结果进行语义精排。
    如果 reranker 不可用，降级为 Qdrant 分数排序。
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.RERANK_MODEL

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """对检索结果重排序

        Args:
            query: 用户查询
            documents: 检索结果列表 (每项需含 "text" 字段)
            top_k: 返回前 N 条

        Returns:
            重排序后的文档列表（按相关性降序）
        """
        if not documents:
            return []

        # 尝试用 qwen3-vl-rerank 做语义精排
        try:
            return await self._dashscope_rerank(query, documents, top_k)
        except Exception as e:
            logger.warning(
                "Reranker '%s' 不可用 (%s)，降级为分数排序",
                self.model_name, e,
            )
            return self._score_fallback(documents, top_k)

    async def _dashscope_rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int,
    ) -> list[dict]:
        """通过阿里云百炼 DashScope 进行语义重排序"""
        import dashscope
        from dashscope import TextReRank

        # 设置自定义 endpoint
        if settings.DASHSCOPE_BASE_URL:
            dashscope.base_http_api_url = settings.DASHSCOPE_BASE_URL

        docs_for_api = [doc.get("text", "") for doc in documents]

        resp = TextReRank.call(
            model=self.model_name,
            query=query,
            documents=docs_for_api,
            top_n=top_k,
            return_documents=True,
            api_key=settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY,
        )

        if resp.status_code != 200:
            logger.error("Rerank API 错误: %s", resp)
            return self._score_fallback(documents, top_k)

        # 解析返回结果
        reranked = []
        for item in resp.output.results:
            idx = item.index
            if idx < len(documents):
                doc = dict(documents[idx])
                doc["rerank_score"] = round(item.relevance_score, 4)
                doc["score"] = doc["rerank_score"]  # 覆盖原分数
                reranked.append(doc)

        reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        logger.info(
            "Rerank 完成: %d → %d 条 (model=%s)",
            len(documents), len(reranked), self.model_name,
        )
        return reranked[:top_k]

    def _score_fallback(self, documents: list[dict], top_k: int) -> list[dict]:
        """降级方案：按 Qdrant 原始分数排序"""
        scored = [
            {**doc, "rerank_score": doc.get("score", 0)}
            for doc in documents
        ]
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]
