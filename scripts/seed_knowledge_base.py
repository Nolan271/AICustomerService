"""种子数据脚本 — 创建初始知识库并导入示例文档

用法: uv run python scripts/seed_knowledge_base.py
"""

import asyncio
import logging

from app.dependencies import get_kb_service, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("开始初始化种子数据 ...")

    async for db in get_db():
        kb_service = await get_kb_service(db)
        break

    # 创建默认知识库
    kb = await kb_service.create_kb(
        name="默认知识库",
        description="系统初始知识库",
    )
    logger.info("创建知识库: id=%s, name=%s", kb.id, kb.name)
    logger.info("种子数据初始化完成 ✓")


if __name__ == "__main__":
    asyncio.run(main())
