"""API 路由 — 系统管理"""

import time

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, func

from app.config import settings
from app.dependencies import get_db, get_qdrant_client
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.feedback import Feedback

router = APIRouter(prefix="/admin", tags=["管理"])


async def verify_admin(admin_key: str = Header(..., alias="X-Admin-Key")):
    """管理员鉴权"""
    if admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(403, "无效的管理员密钥")


@router.get("/health")
async def health_check(
    qdrant = Depends(get_qdrant_client),
):
    """系统健康检查"""
    status = {"status": "ok", "app": settings.APP_NAME}
    try:
        qdrant_info = qdrant.client.get_collections()
        status["qdrant"] = "connected"
        status["collections"] = [c.name for c in qdrant_info.collections]
    except Exception as e:
        status["qdrant"] = f"error: {e}"
    return status


@router.get("/stats")
async def system_stats(
    db=Depends(get_db),
    _=Depends(verify_admin),
):
    """系统统计信息（需管理员密钥）"""
    conv_count = await db.scalar(select(func.count(Conversation.id)))
    msg_count = await db.scalar(select(func.count(Message.id)))
    fb_count = await db.scalar(select(func.count(Feedback.id)))
    avg_rating = await db.scalar(select(func.avg(Feedback.rating)))

    return {
        "conversations": conv_count or 0,
        "messages": msg_count or 0,
        "feedbacks": fb_count or 0,
        "avg_rating": round(float(avg_rating or 0), 2),
        "uptime": time.time(),
    }
