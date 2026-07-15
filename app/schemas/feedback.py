"""Pydantic 模型 — 反馈 API 出入参"""

from typing import Optional

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    message_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    rating: int
    comment: Optional[str] = None
    created_at: Optional[str] = None
