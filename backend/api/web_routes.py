"""Web 路由 - React SPA"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse

logger = logging.getLogger(__name__)

router = APIRouter()
PROJECT_ROOT = Path(__file__).parent.parent.parent
REACT_DIST = PROJECT_ROOT / "frontend" / "web" / "dist"


@router.get("/api/backend-url")
async def get_backend_url(request: Request):
    """返回当前服务 URL（同源）"""
    base = str(request.base_url).rstrip("/")
    return {"backend_url": base}


@router.get("/", response_class=HTMLResponse)
@router.get("/index.html", response_class=HTMLResponse)
async def index(request: Request):
    """主页 - React SPA"""
    index_file = REACT_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse(
        content="<html><body style='font-family:sans-serif;padding:2rem;color:#94a3b8;'>"
        "前端未构建。请运行: <code>cd frontend/react-app && npm install && npm run build</code>"
        "</body></html>",
        status_code=503,
    )


@router.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa(full_path: str):
    """SPA 回退：未匹配的路径返回 index.html，由前端路由处理（如 /wechat-drafts）。"""
    index_file = REACT_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse(
        content="<html><body style='font-family:sans-serif;padding:2rem;color:#94a3b8;'>前端未构建</body></html>",
        status_code=503,
    )


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 流式聊天 - 直接调用 chat stream，无需代理"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id")
            if not message:
                await websocket.send_json({"type": "error", "content": "消息不能为空"})
                continue

            try:
                from backend.api.chat_routes import get_orchestrator
                from backend.api.stream_sender import SSEFormatter
                orchestrator = get_orchestrator()
                context = {}
                if session_id:
                    context["session_id"] = session_id
                if data.get("context_type"):
                    context["context_type"] = data["context_type"]
                async for chunk in orchestrator.stream_process(message, context=context):
                    if chunk:
                        formatted = SSEFormatter.format_chunk(chunk, "streaming")
                        if formatted.startswith("data: "):
                            raw = formatted[6:].strip()
                            if raw and raw != "[DONE]":
                                try:
                                    obj = json.loads(raw)
                                    txt = obj.get("content", "")
                                    if txt:
                                        await websocket.send_json({"type": "chunk", "content": txt})
                                except json.JSONDecodeError:
                                    await websocket.send_json({"type": "chunk", "content": raw})
                await websocket.send_json({"type": "done"})
            except Exception as e:
                logger.error(f"WebSocket 流式聊天错误: {e}", exc_info=True)
                await websocket.send_json({"type": "error", "content": str(e)})
    except WebSocketDisconnect:
        logger.info("WebSocket 连接断开")
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}", exc_info=True)
