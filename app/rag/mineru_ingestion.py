"""
MinerU 文档解析结果摄入模块

MinerU 输出结构（每个 PDF 一个目录）:
├── full.md                      ← 完整 Markdown（含 ![](images/*.jpg) 引用）
├── {uuid}_content_list_v2.json  ← 结构化内容列表
├── {uuid}_origin.pdf            ← 原始 PDF
├── images/                      ← 提取的图片（JPG）
└── layout.json                  ← 版面分析结果

摄入策略:
  → full.md 文本 → 分块 → 向量化 → Qdrant（可检索）
  → images/*   → 路径/元数据 → SQLite（不适合向量化）
  → 表格渲染图  → 路径/描述 → SQLite
  → 页面元数据  → SQLite
"""

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import settings
from app.rag.embedder import EmbeddingService
from app.rag.splitter import get_recursive_splitter
from app.qdrant.client import QdrantClientWrapper

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────────────

@dataclass
class MinerUDoc:
    """单个 MinerU 解析文档的信息"""
    doc_id: str                    # 文档唯一 ID（UUID）
    dir_path: str                  # MinerU 输出目录路径
    original_filename: str         # 原始 PDF 文件名
    full_md_path: str              # full.md 路径
    content_json_path: str         # content_list_v2.json 路径
    image_dir: str                 # images/ 目录路径
    pages: list["MinerUPage"]     # 页面列表


@dataclass
class MinerUPage:
    """单页信息"""
    page_index: int
    blocks: list["MinerUBlock"]


@dataclass
class MinerUBlock:
    """内容块"""
    type: str                      # title | paragraph | image | table | page_number | page_footer | page_header
    content: dict                  # 原始 content 字段
    text: str                      # 提取的纯文本
    bbox: list[float] | None      # 边界框


@dataclass
class ImageRecord:
    """图片记录（存入 SQLite）"""
    doc_id: str
    image_path: str                # 原图路径
    image_filename: str            # UUID.jpg
    alt_text: str                  # 图片说明（上下文文本）
    page_index: int
    block_index: int


@dataclass
class TableRecord:
    """表格记录（存入 SQLite）"""
    doc_id: str
    image_path: str                # 表格渲染图路径
    caption: str                   # 表格标题
    page_index: int
    block_index: int


# ── 解析器 ────────────────────────────────────────────────────────

class MinerUParser:
    """解析 MinerU 输出目录，提取结构化数据"""

    def __init__(self, mineru_base_dir: str = None):
        self.mineru_base_dir = mineru_base_dir or r"C:\Users\muzhi\MinerU"

    def discover_documents(self) -> list[MinerUDoc]:
        """扫描 MinerU 输出目录，返回所有文档列表"""
        docs = []
        for entry in os.listdir(self.mineru_base_dir):
            entry_path = os.path.join(self.mineru_base_dir, entry)
            if not os.path.isdir(entry_path):
                continue

            # 目录名格式: "{原始文件名}.pdf-{uuid}"
            match = re.match(r"^(.+\.pdf)-([a-f0-9\-]{36})$", entry)
            if not match:
                continue

            original_filename = match.group(1)
            doc_uuid = match.group(2)

            # 查找关键文件
            json_file = self._find_json(entry_path)
            full_md = os.path.join(entry_path, "full.md")
            image_dir = os.path.join(entry_path, "images")

            if not json_file or not os.path.exists(full_md):
                logger.warning("跳过不完整目录: %s", entry)
                continue

            # 解析页面
            pages = self._parse_content_json(json_file)

            doc = MinerUDoc(
                doc_id=doc_uuid,
                dir_path=entry_path,
                original_filename=original_filename,
                full_md_path=full_md,
                content_json_path=json_file,
                image_dir=image_dir if os.path.isdir(image_dir) else "",
                pages=pages,
            )
            docs.append(doc)
            logger.info(
                "发现文档: %s | %d 页 | images: %d 张",
                original_filename, len(pages),
                len(os.listdir(image_dir)) if os.path.isdir(image_dir) else 0,
            )

        return docs

    def _find_json(self, dir_path: str) -> Optional[str]:
        """查找 content_list_v2.json（优先）或 content_list.json"""
        for fname in os.listdir(dir_path):
            if fname.endswith("_content_list_v2.json"):
                return os.path.join(dir_path, fname)
        for fname in os.listdir(dir_path):
            if fname.endswith("_content_list.json"):
                return os.path.join(dir_path, fname)
        return None

    def _parse_content_json(self, json_path: str) -> list[MinerUPage]:
        """解析 content_list_v2.json → 页面列表"""
        with open(json_path, "r", encoding="utf-8") as f:
            pages_data = json.load(f)

        pages = []
        for page_idx, page_blocks in enumerate(pages_data):
            blocks = []
            for block_data in page_blocks:
                block_type = block_data.get("type", "unknown")
                content = block_data.get("content", {})
                bbox = block_data.get("bbox")
                text = self._extract_text(block_type, content)
                blocks.append(MinerUBlock(
                    type=block_type,
                    content=content,
                    text=text,
                    bbox=bbox,
                ))
            pages.append(MinerUPage(page_index=page_idx, blocks=blocks))

        return pages

    def _extract_text(self, block_type: str, content: dict) -> str:
        """从不同 block type 中提取纯文本"""
        if not isinstance(content, dict):
            return str(content) if content else ""

        if block_type in ("title",):
            parts = content.get("title_content", [])
            level = content.get("level", 1)
            text = self._join_content_parts(parts)
            return f"{'#' * level} {text}" if text else ""

        elif block_type == "paragraph":
            parts = content.get("paragraph_content", [])
            return self._join_content_parts(parts)

        elif block_type == "table":
            caption_parts = content.get("table_caption", [])
            caption = self._join_content_parts(caption_parts)
            img_path = content.get("image_source", {}).get("path", "")
            cells = content.get("cells", [])
            table_text = self._extract_table_text(cells)
            return f"[表格] {caption}\n{table_text}" if caption else f"[表格]\n{table_text}"

        elif block_type == "image":
            img_path = content.get("image_source", {}).get("path", "")
            caption_parts = content.get("image_caption", [])
            caption = self._join_content_parts(caption_parts)
            return f"[图片: {img_path}] {caption}".strip()

        elif block_type == "page_number":
            return ""

        elif block_type == "page_footer":
            parts = content.get("page_footer_content", [])
            return self._join_content_parts(parts)

        elif block_type == "page_header":
            parts = content.get("page_header_content", [])
            return self._join_content_parts(parts)

        return ""

    def _join_content_parts(self, parts: list) -> str:
        """将 content 中的结构化文本拼成字符串"""
        if not parts:
            return ""
        texts = []
        for part in parts:
            if isinstance(part, dict):
                texts.append(part.get("content", ""))
            elif isinstance(part, str):
                texts.append(part)
        return "".join(texts).strip()

    def _extract_table_text(self, cells: list) -> str:
        """从表格 cells 中提取文本"""
        if not cells:
            return ""
        rows = []
        for row in cells:
            if isinstance(row, list):
                row_text = " | ".join(
                    self._join_content_parts(cell) if isinstance(cell, list)
                    else str(cell) for cell in row
                )
                rows.append(row_text)
        return "\n".join(rows)


    def extract_images(self, doc: MinerUDoc) -> list[ImageRecord]:
        """从文档中提取所有图片记录"""
        records = []
        for page in doc.pages:
            for idx, block in enumerate(page.blocks):
                if block.type != "image":
                    continue
                img_path = block.content.get("image_source", {}).get("path", "")
                caption = block.content.get("image_caption", [])
                alt_text = self._join_content_parts(caption)
                # 尝试从上下文中获取更丰富的说明
                context_text = self._get_surrounding_text(page.blocks, idx)
                full_alt = alt_text or context_text or ""

                records.append(ImageRecord(
                    doc_id=doc.doc_id,
                    image_path=os.path.join(doc.dir_path, img_path) if img_path else "",
                    image_filename=os.path.basename(img_path) if img_path else "",
                    alt_text=full_alt,
                    page_index=page.page_index,
                    block_index=idx,
                ))
        return records

    def extract_tables(self, doc: MinerUDoc) -> list[TableRecord]:
        """从文档中提取表格记录"""
        records = []
        for page in doc.pages:
            for idx, block in enumerate(page.blocks):
                if block.type != "table":
                    continue
                img_path = block.content.get("image_source", {}).get("path", "")
                caption_parts = block.content.get("table_caption", [])
                caption = self._join_content_parts(caption_parts)

                records.append(TableRecord(
                    doc_id=doc.doc_id,
                    image_path=os.path.join(doc.dir_path, img_path) if img_path else "",
                    caption=caption,
                    page_index=page.page_index,
                    block_index=idx,
                ))
        return records

    def _get_surrounding_text(self, blocks: list[MinerUBlock], idx: int, radius: int = 2) -> str:
        """获取指定块周围的文本作为上下文说明"""
        texts = []
        start = max(0, idx - radius)
        end = min(len(blocks), idx + radius + 1)
        for i in range(start, end):
            if i == idx:
                continue
            if blocks[i].type in ("title", "paragraph"):
                texts.append(blocks[i].text)
        return " | ".join(texts[-3:])  # 取最近的 3 条


# ── 摄入流水线 ────────────────────────────────────────────────────

class MinerUIngestionPipeline:
    """
    MinerU → Qdrant + SQLite 摄入流水线

    策略:
    1. full.md → RecursiveCharacterTextSplitter → Embedding → Qdrant
    2. 图片/表格渲染图 → SQLite（不适合向量化）
    3. 文档元数据 → SQLite
    """

    def __init__(
        self,
        embedder: EmbeddingService,
        qdrant: QdrantClientWrapper,
        parser: MinerUParser = None,
    ):
        self.embedder = embedder
        self.qdrant = qdrant
        self.parser = parser or MinerUParser()
        self.splitter = get_recursive_splitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    async def ingest_all(
        self,
        kb_id: str,
        batch_size: int = 20,
    ) -> list[dict]:
        """扫描 MinerU 输出目录，批量摄入所有文档

        Returns:
            摄入结果列表:
            [{
                "doc_id": str,
                "original_filename": str,
                "status": "success" | "failed",
                "chunk_count": int,
                "image_count": int,
                "table_count": int,
                "error": str | None,
            }]
        """
        docs = self.parser.discover_documents()
        logger.info("MinerU 发现 %d 个文档，开始摄入...", len(docs))

        results = []
        for doc in docs:
            try:
                result = await self.ingest_one(doc, kb_id, batch_size)
                results.append(result)
                logger.info(
                    "✓ %s → chunks=%d, images=%d, tables=%d",
                    doc.original_filename,
                    result["chunk_count"],
                    result["image_count"],
                    result["table_count"],
                )
            except Exception as e:
                logger.exception("摄入失败: %s", doc.original_filename)
                results.append({
                    "doc_id": doc.doc_id,
                    "original_filename": doc.original_filename,
                    "status": "failed",
                    "error": str(e),
                    "chunk_count": 0,
                    "image_count": 0,
                    "table_count": 0,
                })

        return results

    async def ingest_one(
        self,
        doc: MinerUDoc,
        kb_id: str,
        batch_size: int = 20,
    ) -> dict:
        """摄入单个 MinerU 文档

        流程:
        1. 读取 full.md → 分块 → 向量化 → upsert Qdrant
        2. 提取图片/表格元数据 → 准备 SQLite 写入
        3. 返回摄入统计
        """
        # ── 第 1 步: 读取 full.md 并分块 ──
        with open(doc.full_md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 提取所有图片引用并建立映射：uuid.jpg → alt_text
        image_map = {}
        for img in self.parser.extract_images(doc):
            image_map[img.image_filename] = img.alt_text

        # 替换 ![](images/uuid.jpg) → [图片: uuid.jpg]，保留图片文件名
        md_clean = re.sub(
            r"!\[(.*?)\]\(images/([^\)]+)\)",
            lambda m: f"[图片: {m.group(2)}]",
            md_content,
        )

        # 使用 RecursiveCharacterTextSplitter 分块
        from langchain_core.documents import Document as LCDocument
        lc_docs = [LCDocument(page_content=md_clean, metadata={"source": doc.original_filename})]
        chunks = self.splitter.split_documents(lc_docs)

        # 提取每个 chunk 中引用的图片
        chunk_images = []
        for chunk in chunks:
            images_in_chunk = re.findall(r"\[图片: ([a-f0-9]+\.jpg)\]", chunk.page_content)
            chunk_images.append(images_in_chunk)

        # ── 第 2 步: 批量向量化并 upsert Qdrant ──
        chunk_count = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.page_content for c in batch]
            vectors = await self.embedder.aembed_documents(texts)

            points = []
            for j, vec in enumerate(vectors):
                point_id = str(uuid.uuid4())
                chunk_text = batch[j].page_content
                chunk_idx = i + j
                images_ref = chunk_images[chunk_idx] if chunk_idx < len(chunk_images) else []
                points.append({
                    "id": point_id,
                    "vector": vec,
                    "payload": {
                        "text": chunk_text,
                        "doc_id": doc.doc_id,
                        "kb_id": kb_id,
                        "doc_name": doc.original_filename,
                        "chunk_index": i + j,
                        "source_type": "mineru_markdown",
                        "images": images_ref,
                        "metadata": {
                            "original_filename": doc.original_filename,
                            "md_path": doc.full_md_path,
                        },
                    },
                })

            await self.qdrant.upsert(points)
            chunk_count += len(points)

        # ── 第 3 步: 提取图片/表格元数据 ──
        images = self.parser.extract_images(doc)
        tables = self.parser.extract_tables(doc)

        # 图片和表格数据写入 SQLite（由上层调用方处理）
        # 这里只返回结构化数据，让调用方决定如何存入 SQLite
        image_records = [
            {
                "doc_id": img.doc_id,
                "image_path": img.image_path,
                "image_filename": img.image_filename,
                "alt_text": img.alt_text,
                "page_index": img.page_index,
            }
            for img in images
        ]
        table_records = [
            {
                "doc_id": tbl.doc_id,
                "image_path": tbl.image_path,
                "caption": tbl.caption,
                "page_index": tbl.page_index,
            }
            for tbl in tables
        ]

        return {
            "doc_id": doc.doc_id,
            "original_filename": doc.original_filename,
            "status": "success",
            "chunk_count": chunk_count,
            "image_count": len(image_records),
            "table_count": len(table_records),
            "error": None,
            "images": image_records,
            "tables": table_records,
        }


# ── 快捷 CLI ──────────────────────────────────────────────────────

async def ingest_mineru_to_qdrant(
    kb_id: str,
    mineru_base_dir: str = None,
) -> list[dict]:
    """快捷入口：扫描 MinerU 输出目录并摄入到 Qdrant

    Args:
        kb_id: 目标知识库 ID
        mineru_base_dir: MinerU 输出根目录，默认 C:\\Users\\muzhi\\MinerU

    Returns:
        摄入结果列表
    """
    from app.dependencies import get_embedder, get_qdrant_client

    embedder = get_embedder()
    qdrant = get_qdrant_client()
    parser = MinerUParser(mineru_base_dir or r"C:\Users\muzhi\MinerU")
    pipeline = MinerUIngestionPipeline(embedder=embedder, qdrant=qdrant, parser=parser)

    return await pipeline.ingest_all(kb_id=kb_id)
