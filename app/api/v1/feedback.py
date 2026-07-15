"""API 路由 — 用户反馈"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func

from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.models.feedback import Feedback
from app.dependencies import get_db
from app.utils.common import generate_uuid

router = APIRouter(prefix="/feedback", tags=["反馈"])


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    data: FeedbackCreate,
    db=Depends(get_db),
):
    """提交用户反馈"""
    fb = Feedback(
        id=generate_uuid(),
        message_id=data.message_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return FeedbackResponse(
        id=fb.id,
        message_id=fb.message_id,
        rating=fb.rating,
        comment=fb.comment,
        created_at=fb.created_at.isoformat() if fb.created_at else None,
    )


@router.get("/stats")
async def feedback_stats(
    db=Depends(get_db),
):
    """反馈统计"""
    result = await db.execute(
        select(
            func.avg(Feedback.rating),
            func.count(Feedback.id),
            func.sum(func.case((Feedback.rating >= 4, 1), else_=0)),
        )
    )
    row = result.one()
    return {
        "avg_rating": round(float(row[0] or 0), 2),
        "total_count": row[1],
        "positive_count": row[2] or 0,
    }
