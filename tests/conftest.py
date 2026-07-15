"""pytest 配置与共享 fixtures"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings


@pytest_asyncio.fixture
async def client():
    """FastAPI 测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    """测试数据库会话（需配置测试专用 DATABASE_URL）"""
    # TODO: 使用独立的测试数据库
    pass
