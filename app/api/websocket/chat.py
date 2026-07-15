"""WebSocket 实时对话处理"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.chat_service import ChatService
from app.dependencies import get_chat_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active[session_id] = ws
        logger.info("WebSocket 已连接: session=%s", session_id)

    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)
        logger.info("WebSocket 已断开: session=%s", session_id)


manager = ConnectionManager()


@router.websocket("/chat/ws")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 实时对话端点

    客户端发送 JSON:
        {"message": "用户问题", "kb_id": "可选"}
    服务端返回 JSON:
        {"event": "token", "data": "片段"}
        {"event": "done", "data": {"answer": "...", "sources": [...]}}
    """
    session_id = websocket.query_params.get("session_id")
    if not session_id:
        await websocket.close(code=4000)
        return

    chat_service: ChatService = await get_chat_service()
    await manager.connect(session_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            user_input = data.get("message", "")
            kb_id = data.get("kb_id")

            result = await chat_service.chat(
                session_id=session_id,
                user_input=user_input,
                kb_id=kb_id,
            )

            await websocket.send_json({"event": "token", "data": result["answer"]})
            await websocket.send_json({
                "event": "done",
                "data": {
                    "sources": result.get("sources", []),
                    "follow_up_questions": result.get("follow_up_questions", []),
                    "intent": result.get("intent"),
                },
            })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.exception("WebSocket 处理异常")
        await websocket.send_json({"event": "error", "data": str(e)})
        manager.disconnect(session_id)
