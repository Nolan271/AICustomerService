"""文本分块策略 — 多种分块策略适配不同文档类型"""

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
    TokenTextSplitter,
)
from langchain_core.documents import Document as LCDocument

from app.config import settings


def get_recursive_splitter(
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> RecursiveCharacterTextSplitter:
    """递归字符分割器 — 通用场景"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.CHUNK_SIZE,
        chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", ".", " ", ""],
        length_function=len,
    )


def get_markdown_splitter() -> MarkdownHeaderTextSplitter:
    """Markdown 标题分割器 — 保留文档层级结构"""
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]
    return MarkdownHeaderTextSplitter(headers_to_split_on)


def get_token_splitter(
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> TokenTextSplitter:
    """Token 级分割器 — 精确控制 Token 数"""
    return TokenTextSplitter(
        chunk_size=chunk_size or settings.CHUNK_SIZE,
        chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
    )


def split_documents(
    documents: list[LCDocument],
    strategy: str = "recursive",
) -> list[LCDocument]:
    """统一分块入口

    Args:
        documents: LangChain Document 列表
        strategy: 分块策略 (recursive | token)

    Returns:
        分块后的 Document 列表
    """
    if strategy == "token":
        splitter = get_token_splitter()
    else:
        splitter = get_recursive_splitter()

    return splitter.split_documents(documents)
