"""LangGraph 节点 — 回答生成

根据检索结果和对话历史生成最终回答。
"""

import logging
import time

from app.llm.factory import LLMFactory
from app.rag.prompt_templates import RAG_PROMPT, CHITCHAT_PROMPT
from app.utils.common import format_chat_history
from app.workflows.state import ChatState

logger = logging.getLogger(__name__)


async def generation_node(state: ChatState) -> dict:
    """生成节点：构造 Prompt → 调用 LLM"""
    start = time.time()
    intent = state.get("intent", "KB_QA")
    llm = LLMFactory.get_fast_model()

    # 闲聊/问候 — 无需知识库上下文
    if intent == "CHITCHAT":
        chat_history = format_chat_history(state.get("messages", []))
        chain = CHITCHAT_PROMPT | llm
        result = await chain.ainvoke({
            "input": state["user_input"],
            "messages": [],
            "chat_history": chat_history,
        })
        elapsed = round((time.time() - start) * 1000)
        return {
            "answer": result.content,
            "processing_steps": [f"闲聊生成 {elapsed}ms"],
        }

    # 转人工
    if intent == "HANDOFF":
        return {
            "answer": "已记录您的问题，正在为您转接人工客服，请稍候。",
            "need_human_handoff": True,
            "handoff_reason": "用户请求转人工",
            "processing_steps": ["转人工"],
        }

    # 数据查询 — data_query_node 已生成回答，直接透传
    if intent == "DATA_QUERY" and state.get("answer"):
        return {
            "answer": state["answer"],
            "chart_config": state.get("chart_config"),
            "sources": state.get("sources", []),
            "processing_steps": ["数据查询结果透传"],
        }

    # 知识问答 / 追问澄清
    import re
    MEDIA_BASE = "http://localhost:8000/api/v1/media/images"

    context_parts = []
    for text, s in zip(
        state.get("context_documents", []) or [],
        state.get("sources", []) or [],
    ):
        text_with_images = re.sub(
            r'\[图片:\s*([^\]]+\.jpg)\]',
            r'[查看图片](' + MEDIA_BASE + r'/\1)',
            text,
        )
        context_parts.append(f"📄 [{s.get('doc_name', '未知文档')}] {text_with_images}")

    context = "\n\n---\n\n".join(context_parts) or "未找到相关知识。"
    chat_history = format_chat_history(state.get("messages", []))

    chain = RAG_PROMPT | llm
    result = await chain.ainvoke({
        "context": context,
        "chat_history": chat_history,
        "input": state["user_input"],
        "messages": [],
    })

    elapsed = round((time.time() - start) * 1000)
    return {
        "answer": result.content,
        "processing_steps": [f"回答生成 {elapsed}ms"],
    }
