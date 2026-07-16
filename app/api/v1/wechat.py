"""API 路由 — 微信公众号/测试号配置验证

微信后台配置时需要验证服务器地址：
  1. 在微信后台填写 URL 和 Token
  2. 微信发 GET 请求到 URL 进行验证
  3. 本接口校验签名后原样返回 echostr
"""

import hashlib
import logging

from fastapi import APIRouter, Request, Response

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wechat", tags=["微信"])


@router.get("")
async def wechat_verify(request: Request):
    """微信服务器配置验证接口（GET）

    微信后台提交配置时，会 GET 请求此接口。
    校验通过后返回 echostr，微信显示"配置成功"。
    """
    # 微信后台填的 Token（必须一致）
    token = settings.WECHAT_TOKEN

    # 微信发来的参数
    signature = request.query_params.get("signature")
    timestamp = request.query_params.get("timestamp")
    nonce = request.query_params.get("nonce")
    echostr = request.query_params.get("echostr")

    logger.info("微信验证请求: signature=%s, timestamp=%s, nonce=%s", signature, timestamp, nonce)

    if not all([signature, timestamp, nonce, echostr]):
        return Response(content="参数不完整", status_code=400)

    # 微信验证算法：sha1(排序[token, timestamp, nonce])
    tmp_list = [token, timestamp, nonce]
    tmp_list.sort()
    tmp_str = "".join(tmp_list)
    hash_str = hashlib.sha1(tmp_str.encode("utf-8")).hexdigest()

    if hash_str == signature:
        # 验证通过，原样返回 echostr（纯文本，不能 JSON 包装）
        logger.info("微信验证通过 ✅")
        return Response(content=echostr, media_type="text/plain")
    else:
        logger.warning("微信验证失败: hash=%s, signature=%s", hash_str, signature)
        return Response(content="验证失败", status_code=403)


@router.post("")
async def wechat_message(request: Request):
    """接收微信用户消息（POST）

    配置成功后，用户给公众号发消息时，微信会 POST 到此接口。
    当前只返回成功，后续可按需处理。
    """
    body = await request.body()
    logger.info("收到微信消息: %s", body.decode("utf-8", errors="replace")[:500])
    return {"code": 200, "msg": "success"}
