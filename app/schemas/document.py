"""Pydantic 模型 — 文档 API 出入参"""

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: Optional[int] = None
    status: str
    chunk_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class DocumentList(BaseModel):
    items: list[DocumentResponse]
    total: int
