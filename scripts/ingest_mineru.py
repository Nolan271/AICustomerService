"""
MinerU 文档摄入脚本

将 MinerU 解析产出的文档摄入到系统中：
  - full.md 文本 → 分块 → Embedding → Qdrant（可向量化部分）
  - 图片/表格 → 路径元数据 → SQLite（不可向量化部分）

用法:
  # 摄入所有 MinerU 文档到指定知识库
  uv run python scripts/ingest_mineru.py --kb-name "充电桩知识库"

  # 摄入到已有知识库
  uv run python scripts/ingest_mineru.py --kb-id <kb-uuid>

  # 指定 MinerU 输出目录
  uv run python scripts/ingest_mineru.py --mineru-dir "C:/Users/muzhi/MinerU" --kb-name "知识库"

  # 试运行（不实际写入）
  uv run python scripts/ingest_mineru.py --dry-run
"""

import asyncio
import argparse
import logging
import os
import sys

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select

from app.config import settings
from app.db.init_db import init_database
from app.db.session import async_session_factory
from app.dependencies import get_embedder, get_qdrant_client
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document, DocumentStatus
from app.models.mineru_asset import DocumentImage, DocumentTable
from app.rag.mineru_ingestion import MinerUParser, MinerUIngestionPipeline
from app.utils.common import generate_uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def ensure_knowledge_base(kb_name: str, kb_id: str | None) -> str:
    """确保知识库存在，返回 kb_id"""
    async with async_session_factory() as db:
        if kb_id:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            kb = result.scalar_one_or_none()
            if kb:
                logger.info("使用已有知识库: %s (%s)", kb.name, kb.id)
                return kb.id
            logger.warning("指定知识库不存在: %s，将自动创建", kb_id)

        # 创建新知识库
        kb = KnowledgeBase(
            id=kb_id or generate_uuid(),
            name=kb_name or "MinerU 导入知识库",
            description=f"通过 MinerU 摄入脚本自动导入 ({__file__})",
        )
        db.add(kb)
        await db.commit()
        logger.info("创建知识库: %s (%s)", kb.name, kb.id)
        return kb.id


async def store_assets_to_sqlite(
    results: list[dict],
    kb_id: str,
):
    """将非向量资产（图片、表格）存入 SQLite"""
    async with async_session_factory() as db:
        image_count = 0
        table_count = 0

        for doc_result in results:
            if doc_result["status"] != "success":
                continue

            # 先创建 Document 记录
            doc_record = Document(
                id=generate_uuid(),
                kb_id=kb_id,
                filename=doc_result["original_filename"],
                file_type="pdf",
                status=DocumentStatus.READY,
                chunk_count=doc_result["chunk_count"],
            )
            db.add(doc_record)

            # 存储图片记录
            for img in doc_result.get("images", []):
                doc_img = DocumentImage(
                    doc_id=doc_result["doc_id"],
                    kb_id=kb_id,
                    original_filename=doc_result["original_filename"],
                    image_filename=img["image_filename"],
                    image_path=img["image_path"],
                    alt_text=img["alt_text"],
                    page_index=img["page_index"],
                    file_size=(
                        os.path.getsize(img["image_path"])
                        if img["image_path"] and os.path.isfile(img["image_path"])
                        else None
                    ),
                )
                db.add(doc_img)
                image_count += 1

            # 存储表格记录
            for tbl in doc_result.get("tables", []):
                doc_tbl = DocumentTable(
                    doc_id=doc_result["doc_id"],
                    kb_id=kb_id,
                    original_filename=doc_result["original_filename"],
                    image_path=tbl["image_path"],
                    caption=tbl["caption"],
                    page_index=tbl["page_index"],
                )
                db.add(doc_tbl)
                table_count += 1

        await db.commit()
        logger.info("SQLite 写入完成: images=%d, tables=%d", image_count, table_count)


async def main():
    parser = argparse.ArgumentParser(
        description="MinerU 文档摄入: → Qdrant(文本向量) + SQLite(图片/表格)"
    )
    parser.add_argument("--kb-id", help="目标知识库 ID（如不指定则按名称创建）")
    parser.add_argument(
        "--kb-name", default="MinerU 导入知识库", help="知识库名称（新建时使用）"
    )
    parser.add_argument(
        "--mineru-dir",
        default=r"C:\Users\muzhi\MinerU",
        help="MinerU 输出根目录",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行：只扫描不写入",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("MinerU 文档摄入流水线")
    logger.info("   MinerU 目录: %s", args.mineru_dir)
    logger.info("   知识库: %s", args.kb_name if not args.kb_id else f"ID={args.kb_id}")
    logger.info("   模式: %s", "试运行 (DRY RUN)" if args.dry_run else "正式写入")
    logger.info("=" * 60)

    # 第 1 步：扫描 MinerU 输出
    logger.info("\n[1/4] 扫描 MinerU 输出目录...")
    parser_obj = MinerUParser(args.mineru_dir)
    docs = parser_obj.discover_documents()
    if not docs:
        logger.warning("未发现有效的 MinerU 文档，退出。")
        return

    total_pages = sum(len(d.pages) for d in docs)
    logger.info("发现 %d 个文档，共 %d 页", len(docs), total_pages)

    if args.dry_run:
        for d in docs:
            images = parser_obj.extract_images(d)
            tables = parser_obj.extract_tables(d)
            logger.info(
                "  📄 %s → %d 页, %d 图片, %d 表格",
                d.original_filename, len(d.pages), len(images), len(tables),
            )
        logger.info("\n试运行完成，未写入任何数据。")
        return

    # 第 2 步：初始化数据库表（先于知识库创建）
    logger.info("\n[2/4] 初始化数据库...")
    await init_database()

    # 第 3 步：确保知识库存在
    logger.info("\n[3/4] 确保知识库...")
    kb_id = await ensure_knowledge_base(args.kb_name, args.kb_id)

    # 第 4 步：执行摄入
    logger.info("\n[4/4] 开始摄入到 Qdrant + SQLite...")
    embedder = get_embedder()
    qdrant = get_qdrant_client()
    pipeline = MinerUIngestionPipeline(
        embedder=embedder,
        qdrant=qdrant,
        parser=parser_obj,
    )

    results = await pipeline.ingest_all(kb_id=kb_id)

    # 存入 SQLite（图片/表格元数据）
    await store_assets_to_sqlite(results, kb_id)

    # 输出统计
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    total_chunks = sum(r["chunk_count"] for r in success)
    total_images = sum(r["image_count"] for r in success)
    total_tables = sum(r["table_count"] for r in success)

    logger.info("=" * 60)
    logger.info("摄入完成!")
    logger.info("   成功: %d / %d", len(success), len(results))
    logger.info("   失败: %d", len(failed))
    logger.info("   文本分块 → Qdrant: %d 个向量", total_chunks)
    logger.info("   图片     → SQLite: %d 条", total_images)
    logger.info("   表格     → SQLite: %d 条", total_tables)
    if failed:
        logger.warning("失败详情:")
        for f in failed:
            logger.warning("   ✗ %s: %s", f["original_filename"], f["error"])
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
