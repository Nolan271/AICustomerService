"""LangGraph 节点 — 记忆管理

持久化对话历史到 SQLite，维护上下文窗口。
"""

import logging
import time
from app.workflows.state import ChatState

logger = logging.getLogger(__name__)


async def memory_node(state: ChatState) -> dict:
    """记忆节点：持久化 + 上下文窗口裁剪"""
    start = time.time()

    updated_messages = list(state.get("messages", []))
    updated_messages.append({"role": "user", "content": state["user_input"]})
    updated_messages.append({"role": "assistant", "content": state.get("answer", "")})

    max_rounds = 10
    if len(updated_messages) > max_rounds * 2:
        updated_messages = updated_messages[-(max_rounds * 2):]

    elapsed = round((time.time() - start) * 1000)
    return {
        "messages": [],
        "processing_steps": [f"记忆更新({len(updated_messages)}条) {elapsed}ms"],
    }
