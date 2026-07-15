"""API 路由 — 会话管理"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.schemas.session import SessionCreate, SessionResponse, SessionList, MessageResponse
from app.models.conversation import Conversation
from app.models.message import Message
from app.dependencies import get_db
from app.utils.common import generate_uuid

router = APIRouter(prefix="/sessions", tags=["会话"])


@router.get("", response_model=SessionList)
async def list_sessions(
    user_id: str | None = None,
    db=Depends(get_db),
):
    """获取会话列表"""
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())
    if user_id:
        stmt = stmt.where(Conversation.user_id == user_id)
    result = await db.execute(stmt)
    sessions = list(result.scalars().all())
    return SessionList(
        items=[SessionResponse.model_validate(s) for s in sessions],
        total=len(sessions),
    )


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreate,
    db=Depends(get_db),
):
    """创建新会话"""
    session = Conversation(
        id=data.id or generate_uuid(),
        user_id=data.user_id,
        kb_id=data.kb_id,
        title=data.title,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db=Depends(get_db),
):
    """获取会话详情"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "会话不存在")
    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db=Depends(get_db),
):
    """删除会话"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "会话不存在")
    await db.delete(session)
    await db.commit()


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: str,
    db=Depends(get_db),
):
    """获取会话消息历史"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == session_id)
        .order_by(Message.created_at)
    )
    messages = list(result.scalars().all())

    def to_response(m):
        import json
        meta = None
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
            except (json.JSONDecodeError, TypeError):
                meta = None
        return MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role.value if hasattr(m.role, 'value') else m.role,
            content=m.content,
            metadata=meta,
            created_at=m.created_at,
        )

    return [to_response(m) for m in messages]
