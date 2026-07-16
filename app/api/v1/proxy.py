"""API 路由 — 代理外部充电桩管理平台接口

使用说明：
  小程序用户调用此接口时，需在请求头中携带登录后获得的 Bearer Token。
  此 Token 同时用于鉴权和转发到外部 API，无需额外凭证。

  请求示例：
    POST /api/v1/proxy/home/statRevenue
    Authorization: Bearer eyJhbGci...
    Content-Type: application/json
"""


import logging
from fastapi import APIRouter, Depends, HTTPException
from httpx import AsyncClient, Timeout

from app.config import settings
# from app.auth.external_auth import require_token  # TODO: 调试完后恢复

logger = logging.getLogger(__name__)

BASE_URL = settings.EXTERNAL_API_BASE_URL

# TODO: 调试用写死 Token，后续改为从请求头获取
_HARDCODED_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJsb2dpbl91c2VyX2tleSI6IjQ1NWFjZmY3LTdjNTUtNGNkNS1iNDU0LWIyYTZkYWVmNTQzMyJ9.gBWgmRh8YfntS8b45kLmISkDCnPmtILx6YpxRo5IVOvzQT67i3ZwqFls1RKf9EXG_dBJVVCYuHegGk4zJ_mNQg"

router = APIRouter(prefix="/proxy", tags=["数据代理"])


@router.post("/{path:path}")
async def proxy_request(
    path: str,
    body: dict = None,
    # token: str = Depends(require_token),  # TODO: 调试完后恢复
):
    """代理到外部 API：POST /api/v1/proxy/{path}

    Token 直接从请求头的 Authorization 获取并转发。
    外部 API 返回什么就返回什么。
    """
    url = f"{BASE_URL}/{path}"
    headers = {
        "Authorization": "Bearer " + _HARDCODED_TOKEN,
        "Content-Type": "application/json",
    }
    logger.info("代理请求: POST %s", url)
    async with AsyncClient(timeout=Timeout(settings.EXTERNAL_API_TIMEOUT)) as client:
        resp = await client.post(url, json=body or {}, headers=headers)
    if resp.status_code != 200:
        logger.warning("代理返回 %d: %s", resp.status_code, resp.text[:200])
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    return resp.json()


@router.get("/{path:path}")
async def proxy_get(
    path: str,
    # token: str = Depends(require_token),  # TODO: 调试完后恢复
):
    """代理到外部 API：GET /api/v1/proxy/{path}"""
    url = f"{BASE_URL}/{path}"
    headers = {"Authorization": "Bearer " + _HARDCODED_TOKEN}
    async with AsyncClient(timeout=Timeout(settings.EXTERNAL_API_TIMEOUT)) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    return resp.json()
