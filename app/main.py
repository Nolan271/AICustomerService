"""FastAPI 应用入口 — AiCustomerService"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.init_db import init_database
from app.dependencies import get_qdrant_client
from app.qdrant.client import QdrantConnectionError

# ── 日志配置 ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── 生命周期管理 ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的资源管理"""
    logger.info("=" * 50)
    logger.info("  %s 启动中 ...", settings.APP_NAME)
    logger.info("  模型: %s | 嵌入: %s (%s)",
                settings.OPENAI_MODEL, settings.EMBEDDING_MODEL, settings.EMBEDDING_PROVIDER)
    logger.info("  Qdrant: %s:%s", settings.QDRANT_HOST, settings.QDRANT_PORT)
    logger.info("=" * 50)

    # 启动时初始化
    await init_database()

    qdrant = get_qdrant_client()
    if qdrant.is_connected:
        try:
            await qdrant.ensure_collection()
            count = await qdrant.count()
            logger.info("  Qdrant 就绪 | 当前向量数: %d", count)
        except QdrantConnectionError as e:
            logger.warning("  ⚠ Qdrant 不可用: %s", e)
    else:
        logger.warning(
            "  ⚠ Qdrant 未连接，向量检索功能不可用。\n"
            "     启动方法: uv run python scripts/start_qdrant.py"
        )

    logger.info("  %s 启动完成", settings.APP_NAME)
    yield

    # 关闭时释放资源
    qdrant.close()
    logger.info("  %s 已关闭", settings.APP_NAME)


# ── 创建应用实例 ──────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="基于 RAG 的 AI 智能客服问答系统 | 阿里云百炼 MaaS",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 中间件 — 开发环境允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 注册路由 ──────────────────────────────────────────────────────
from app.api.v1.chat import router as chat_router
from app.api.v1.knowledge_base import router as kb_router
from app.api.v1.document import router as doc_router
from app.api.v1.session import router as session_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.admin import router as admin_router
from app.api.websocket.chat import router as ws_router
from app.api.v1.media import router as media_router
from app.api.v1.proxy import router as proxy_router
from app.api.v1.wechat import router as wechat_router

app.include_router(chat_router, prefix="/api/v1")
app.include_router(kb_router, prefix="/api/v1")
app.include_router(doc_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")
app.include_router(wechat_router)  # 微信验证不需要 /api/v1 前缀
app.include_router(proxy_router, prefix="/api/v1")

# ── 挂载静态文件 ─────────────────────────────────────────────────
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/chat", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    app.mount("/ai-widget", StaticFiles(directory=str(frontend_dir)), name="ai-widget")

# ── 挂载图片目录（开发模式用，生产环境由 Nginx 代理） ──────────
from app.config import settings
media_dir = Path(__file__).resolve().parent.parent / "./data/media/images"
if media_dir.exists():
    app.mount("/media/images", StaticFiles(directory=str(media_dir)), name="media")
