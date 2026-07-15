"""数据库连接与会话管理 — 异步 SQLAlchemy"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},  # SQLite 需要
)

# 会话工厂
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)
