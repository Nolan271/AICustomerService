"""Pydantic 模型 — 会话 API 出入参"""

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    kb_id: Optional[str] = None
    title: str = "新对话"


class SessionResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    kb_id: Optional[str] = None
    title: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class SessionList(BaseModel):
    items: list[SessionResponse]
    total: int


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
