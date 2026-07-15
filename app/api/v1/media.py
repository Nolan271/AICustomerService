"""API 路由 — 媒体文件服务（MinerU 图片等）"""

import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.models.mineru_asset import DocumentImage
from app.dependencies import get_db

router = APIRouter(prefix="/media", tags=["媒体"])


@router.get("/images/{image_filename}")
async def get_image(
    image_filename: str,
    db=Depends(get_db),
):
    """通过图片文件名获取图片"""
    result = await db.execute(
        select(DocumentImage).where(
            DocumentImage.image_filename == image_filename
        ).limit(1)
    )
    img = result.scalar_one_or_none()
    if not img or not img.image_path:
        raise HTTPException(404, "图片不存在")
    if not os.path.isfile(img.image_path):
        raise HTTPException(404, "图片文件已被移动或删除")
    return FileResponse(img.image_path, media_type="image/jpeg")
