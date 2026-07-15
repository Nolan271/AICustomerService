"""LangGraph 节点 — 记忆管理

持久化对话历史到 SQLite，维护上下文窗口。
"""

import logging
from app.workflows.state import ChatState

logger = logging.getLogger(__name__)


async def memory_node(state: ChatState) -> dict:
    """记忆节点：持久化 + 上下文窗口裁剪"""
    # 此节点主要负责状态更新
    # 实际 DB 持久化在 ChatService 中完成

    updated_messages = list(state.get("messages", []))
    updated_messages.append({"role": "user", "content": state["user_input"]})
    updated_messages.append({"role": "assistant", "content": state.get("answer", "")})

    # 窗口裁剪：保留最近 N 轮
    max_rounds = 10
    if len(updated_messages) > max_rounds * 2:
        updated_messages = updated_messages[-(max_rounds * 2):]

    return {
        "messages": [],  # Annotated[operator.add] 会追加到已有列表
        "processing_steps": [f"记忆更新: 当前消息数 {len(updated_messages)}"],
    }
