"""LangGraph 对话工作流 — State 定义"""

import operator
from typing import Annotated, Optional, TypedDict


class ChatState(TypedDict):
    """LangGraph 对话状态 — 贯穿整个工作流的中央数据结构"""

    # ── 输入 ──
    session_id: str
    user_input: str
    user_id: Optional[str]
    user_token: Optional[str]              # 外部 API 的 Bearer Token
    kb_id: Optional[str]

    # ── 中间状态 ──
    intent: Optional[str]                         # 路由节点识别出的意图
    query_embedding: Optional[list[float]]         # 用户问题的向量
    retrieved_chunks: Optional[list[dict]]         # 检索结果（原始）
    reranked_chunks: Optional[list[dict]]          # 重排序后的结果
    context_documents: Optional[list[str]]         # 组装后的上下文文本

    # ── 对话历史 ──
    messages: Annotated[list[dict], operator.add]  # 历史消息（累加）
    history_summary: Optional[str]                 # 长对话摘要

    # ── 输出 ──
    answer: Optional[str]
    chart_config: Optional[dict]                   # 图表配置（数据查询用）
    sources: Optional[list[dict]]                  # 引用来源
    follow_up_questions: Optional[list[str]]       # 建议追问
    need_human_handoff: bool
    handoff_reason: Optional[str]

    # ── 元数据 ──
    error: Optional[str]
    processing_steps: list[str]
    latency_ms: Optional[float]
