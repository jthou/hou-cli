"""路由定义"""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.core.agent.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求（非流式）"""
    try:
        response = await orchestrator.process(request.message)
        return {"response": response, "status": "success"}
    except Exception as e:
        return {
            "response": None,
            "status": "error",
            "error": str(e)
        }

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """处理聊天请求（流式 SSE）"""
    async def generate():
        try:
            async for chunk in orchestrator.stream_process(request.message):
                # SSE 格式：data: {json}\n\n
                yield f"data: {json.dumps({'content': chunk, 'status': 'streaming'})}\n\n"
            # 发送完成信号
            yield f"data: {json.dumps({'content': '', 'status': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'content': '', 'status': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )

