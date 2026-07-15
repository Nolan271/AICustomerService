"""Pydantic 模型 — 对话 API 出入参"""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求"""
    session_id: str = Field(..., description="会话 ID")
    message: str = Field(..., description="用户消息", min_length=1, max_length=4000)
    kb_id: Optional[str] = Field(None, description="知识库 ID（可选）")
    user_id: Optional[str] = Field(None, description="用户标识")
    intent_hint: Optional[str] = Field(None, description="意图提示，前端分类按钮传入：DATA_QUERY | KB_QA")


class SourceItem(BaseModel):
    """引用来源"""
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    doc_name: Optional[str] = None
    text: Optional[str] = None
    score: Optional[float] = None
    metadata: Optional[dict] = None


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    answer: str
    sources: list[SourceItem] = []
    follow_up_questions: list[str] = []
    intent: Optional[str] = None
    need_human_handoff: bool = False
    handoff_reason: Optional[str] = None
    chart_config: Optional[dict] = None
