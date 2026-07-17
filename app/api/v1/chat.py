"""API 路由 — 对话模块

鉴权方式：统一使用外部 API 的 Bearer Token
  Authorization: Bearer <小程序登录后拿到的 Token>
"""

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.core.chat_service import ChatService
from app.dependencies import get_chat_service
# from app.auth.external_auth import require_token  # TODO: 调试完后恢复

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("/completions", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    # token: str = Depends(require_token),  # TODO: 调试完后恢复
):
    """非流式对话 — 单次问答

    需要 Authorization: Bearer <外部API的Token>
    Token 同时用于鉴权和数据查询时的外部 API 调用。
    """
    # 调试用 Token — 替换为当前要测试的账户
    _debug_token = "eyJhbGciOiJIUzUxMiJ9.eyJsb2dpbl91c2VyX2tleSI6IjQxZWFlYzEwLTkyYmMtNDBiNi04OTFkLTNlZGEzNTU0YjVlYiJ9.KKsAAzs3ap_PGR5HANlgu8tysCo5FtxZsNw2Kthq94HIVqbSiE78ATFntWneyUjaOmc-YBI4Y_i_ZSysWTUs3Q"

    result = await chat_service.chat(
        session_id=request.session_id,
        user_input=request.message,
        kb_id=request.kb_id,
        user_id=request.user_id,
        user_token=_debug_token,
        intent_hint=request.intent_hint,
    )

    return ChatResponse(
        session_id=request.session_id,
        answer=result["answer"],
        sources=result.get("sources") or [],
        follow_up_questions=result.get("follow_up_questions") or [],
        intent=result.get("intent"),
        need_human_handoff=result.get("need_human_handoff") or False,
        handoff_reason=result.get("handoff_reason"),
        chart_config=result.get("chart_config"),
    )


@router.post("/completions/stream")
async def chat_completion_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    # token: str = Depends(require_token),  # TODO: 调试完后恢复
):
    """流式对话 — SSE (Server-Sent Events)

    鉴权方式同 /completions
    """
    async def event_generator():
        async for chunk in chat_service.chat_stream(
            session_id=request.session_id,
            user_input=request.message,
            kb_id=request.kb_id,
            user_id=request.user_id,
        ):
            t = chunk.get("type", "")
            if t == "start":
                yield {"event": "start", "data": chunk.get("intent", "")}
            elif t == "token":
                yield {"event": "token", "data": chunk.get("data", "")}
            elif t == "sources":
                import json
                yield {"event": "sources", "data": json.dumps(chunk.get("data", []), ensure_ascii=False)}
            elif t == "meta":
                import json
                yield {"event": "meta", "data": json.dumps(chunk)}
            elif t == "done":
                yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
