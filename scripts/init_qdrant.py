"""初始化 Qdrant 集合 — 手动执行: uv run python scripts/init_qdrant.py"""

import asyncio
import logging

from app.config import settings
from app.dependencies import get_qdrant_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("初始化 Qdrant 集合 '%s' ...", settings.QDRANT_COLLECTION)
    qdrant = get_qdrant_client()
    await qdrant.ensure_collection()
    count = await qdrant.count()
    logger.info("当前向量数: %d", count)
    logger.info("Qdrant 初始化完成 ✓")


if __name__ == "__main__":
    asyncio.run(main())
