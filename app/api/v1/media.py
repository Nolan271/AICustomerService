"""API 路由 — 媒体文件服务

图片统一存储在 data/media/images/ 目录下。
生产环境建议由 Nginx 直接 serve，不走 Python。
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter(prefix="/media", tags=["媒体"])

# 图片存储目录
MEDIA_DIR = Path(settings.MEDIA_DIR)


@router.get("/images/{image_filename}")
async def get_image(image_filename: str):
    """通过文件名获取图片 — 从 data/media/images/ 直接读取"""
    # 安全校验：防止路径穿越
    filename = Path(image_filename).name
    file_path = MEDIA_DIR / filename

    if not file_path.exists():
        raise HTTPException(404, "图片不存在")

    # 根据扩展名返回合适的 Content-Type
    ext = file_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = mime_map.get(ext, "application/octet-stream")

    return FileResponse(str(file_path), media_type=media_type)
