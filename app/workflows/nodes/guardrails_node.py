"""LangGraph 节点 — 安全护栏

对生成的回答进行合规性检查、格式标准化。
"""

import logging
import time
from app.workflows.state import ChatState

logger = logging.getLogger(__name__)


_SENSITIVE_PATTERNS = [
    "银行卡号", "密码", "身份证号", "验证码",
    "转账", "汇款",
]


async def guardrails_node(state: ChatState) -> dict:
    """护栏节点：敏感信息检测 + 格式规范"""
    start = time.time()
    answer = state.get("answer", "")
    modifications = []

    for pattern in _SENSITIVE_PATTERNS:
        if pattern in answer:
            modifications.append(f"检测到敏感词: {pattern}")

    if answer and len(answer) > 4000:
        answer = answer[:4000] + "\n\n...（回答被截断，如需更多信息请继续提问）"
        modifications.append("回答超长截断")

    elapsed = round((time.time() - start) * 1000)
    return {
        "answer": answer,
        "chart_config": state.get("chart_config"),
        "processing_steps": modifications or [f"护栏检查 {elapsed}ms"],
    }
