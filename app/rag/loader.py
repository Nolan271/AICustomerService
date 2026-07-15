"""文档加载器 — 按文件类型自动路由到对应加载器"""

from pathlib import Path
from langchain_core.documents import Document as LCDocument


def get_loader(file_path: str, file_type: str):
    """根据文件类型返回对应的 LangChain 文档加载器"""
    ext = file_type.lower()

    if ext == "pdf":
        from langchain_community.document_loaders import PyMuPDFLoader
        return PyMuPDFLoader(file_path)

    elif ext == "txt":
        from langchain_community.document_loaders import TextLoader
        return TextLoader(file_path, encoding="utf-8")

    elif ext == "md":
        from langchain_community.document_loaders import UnstructuredMarkdownLoader
        return UnstructuredMarkdownLoader(file_path)

    elif ext == "docx":
        from langchain_community.document_loaders import Docx2txtLoader
        return Docx2txtLoader(file_path)

    elif ext == "csv":
        from langchain_community.document_loaders import CSVLoader
        return CSVLoader(file_path)

    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def load_document(file_path: str, file_type: str) -> list[LCDocument]:
    """加载文档并返回 LangChain Document 列表"""
    loader = get_loader(file_path, file_type)
    return loader.load()
