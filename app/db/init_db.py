"""数据库初始化 — 创建所有表"""

import logging

from app.db.session import engine
from app.models.base import Base
import app.models  # noqa: F401 — 一次性导入所有模型

logger = logging.getLogger(__name__)


async def init_database():
    """创建所有未存在的表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建/验证完成")
