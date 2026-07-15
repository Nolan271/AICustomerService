"""LangGraph 节点 — 知识检索

对用户问题进行向量化并在 Qdrant 中检索相关文档片段。
"""

import logging

from app.workflows.state import ChatState

logger = logging.getLogger(__name__)


async def retrieval_node(state: ChatState) -> dict:
    """检索节点：向量化 → Qdrant 搜索"""
    # 延迟导入避免循环依赖
    from app.dependencies import get_retriever
    retriever = get_retriever()

    results = await retriever.retrieve(
        query=state["user_input"],
        kb_id=state.get("kb_id"),
    )

    contexts = []
    sources = []

    for r in results:
        contexts.append(r["text"])
        sources.append({
            "doc_id": r.get("doc_id"),
            "chunk_id": str(r.get("id", "")),
            "doc_name": r.get("doc_name", ""),
            "text": r["text"][:200],
            "score": round(r.get("score", 0), 4),
        })

    return {
        "retrieved_chunks": results,
        "context_documents": contexts,
        "sources": sources,
        "processing_steps": [f"检索到 {len(contexts)} 个相关片段"],
    }
