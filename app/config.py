"""应用配置 — 基于 pydantic-settings 的分层配置管理"""

from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，按 env_file / 环境变量加载"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 应用 ----
    APP_NAME: str = "AiCustomerService"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: Optional[List[str]] = None   # 生产环境: ["https://app.com"]

    # ---- LLM ----
    LLM_PROVIDER: str = "openai"             # openai | ollama | dashscope
    OPENAI_API_KEY: Optional[str] = None      # 兼容 OpenAI / 阿里云百炼
    OPENAI_BASE_URL: Optional[str] = None     # 阿里云百炼: /compatible-mode/v1
    OPENAI_MODEL: str = "qwen3.7-plus"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2:7b"

    # ---- Embedding ----
    # provider: openai | dashscope | ollama
    # - openai:    通过 OpenAI 兼容接口（适合阿里云百炼 OpenAI 兼容模式）
    # - dashscope: 通过阿里云 DashScope SDK（推荐，支持 text-embedding-v3）
    EMBEDDING_PROVIDER: str = "dashscope"
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_BASE_URL: Optional[str] = None   # 阿里云百炼: /api/v1
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # ---- Qdrant ----
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "knowledge_base"
    QDRANT_VECTOR_SIZE: int = 1024            # text-embedding-v3 = 1024 维

    # ---- 数据库 ----
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sqlite/app.db"

    # ---- RAG ----
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RETRIEVAL: int = 5
    TOP_K_RERANK: int = 3
    RETRIEVAL_SCORE_THRESHOLD: float = 0.7
    RERANK_MODEL: str = "qwen3-vl-rerank"       # 重排序模型（你已开通）

    # ---- 对话 ----
    MAX_HISTORY_LENGTH: int = 10
    STREAMING: bool = True
    TEMPERATURE: float = 0.3

    # ---- 知识库 ----
    UPLOAD_DIR: str = "./data/uploads"
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".txt", ".md", ".docx", ".csv"]

    # ---- 管理员 ----
    ADMIN_API_KEY: str = "admin-secret-key"

    # ---- 外部充电桩 API（小程序对接的平台） ----
    EXTERNAL_API_BASE_URL: str = "https://evapp.xingkeele.com/prod-api"
    EXTERNAL_API_TIMEOUT: int = 30


# 全局单例
settings = Settings()
