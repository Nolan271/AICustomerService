"""健康检查端点测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """测试 /admin/health 返回正常"""
    response = await client.get("/api/v1/admin/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
