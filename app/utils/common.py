"""通用工具函数"""

import uuid
from datetime import datetime, timezone


def generate_uuid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_chat_history(messages: list[dict]) -> str:
    """将消息列表格式化为 LLM 对话历史字符串"""
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines[-20:])  # 最多保留 20 条
