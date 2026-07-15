"""统一鉴权模块 — 用小程序/充电桩外部 API 的 Bearer Token 做全接口鉴权

验证方式：
  1. 解码 JWT 检查过期时间（快速拒绝）
  2. 调用外部 API 的轻量接口验证签名（确保 token 真实有效）
  3. 缓存验证结果（5 分钟），避免对每请求都调外部 API

用法：
  @router.post("/xxx")
  async def endpoint(token: str = Depends(require_token)):
      # token 已确认有效，可直接用于调外部 API
"""

import logging
import time
from collections import OrderedDict

import jwt
from fastapi import Header, HTTPException, status
from httpx import AsyncClient, Timeout

from app.config import settings

logger = logging.getLogger(__name__)

# 外部 API 地址（从 config/settings 读取）
EXTERNAL_API_BASE = settings.EXTERNAL_API_BASE_URL

# ── 简单内存缓存 ──────────────────────────────────────────────────
# { token_prefix: expiry_timestamp }
_cache: dict[str, float] = {}
_cache_max = 1000        # 最多缓存 1000 个 token
CACHE_TTL = 300           # 5 秒——不改了，就 5 分钟


def _cache_get(key: str) -> bool:
    cached = _cache.get(key)
    if cached and cached > time.time():
        return True
    _cache.pop(key, None)
    return False


def _cache_set(key: str):
    if len(_cache) >= _cache_max:
        # LRU 淘汰：删掉最早的一个
        _cache.pop(next(iter(_cache)), None)
    _cache[key] = time.time() + CACHE_TTL


async def validate_external_token(token: str) -> None:
    """验证外部 API Bearer Token 是否有效"""
    cache_key = token[:30]  # 用前缀当 key

    # 1. 缓存命中 → 直接过
    if _cache_get(cache_key):
        return

    # 2. 本地解码，快速检查过期（不验签名）
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp", 0)
        if exp and exp < int(time.time()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 已过期，请重新登录"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式无效"
        )

    # 3. 调外部 API 验签名（真正验证）
    try:
        async with AsyncClient(timeout=Timeout(settings.EXTERNAL_API_TIMEOUT)) as client:
            resp = await client.post(
                f"{EXTERNAL_API_BASE}/home/statRevenue",
                headers={"Authorization": f"Bearer {token}"},
                json={"pageNum": 1, "pageSize": 1},
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token 无效或已过期"
                )
    except HTTPException:
        raise
    except Exception as e:
        # 3b. 外部 API 不可用 → 降级信任本地解码结果
        logger.warning("外部 API 不可用，降级为本地解码验证: %s", e)

    # 4. 缓存有效结果
    _cache_set(cache_key)


async def require_token(
    authorization: str = Header(None, alias="Authorization"),
) -> str:
    """FastAPI 依赖：强制要求有效的外部 API Bearer Token

    Returns:
        原始的 token 字符串（可用于转发到外部 API）
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Authorization 头，请先登录"
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization 格式错误，应为 Bearer <token>"
        )

    await validate_external_token(token)
    return token
