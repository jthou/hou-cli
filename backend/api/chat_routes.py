"""聊天相关路由"""
import traceback
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.agent.orchestrator import Orchestrator
from backend.api.stream_sender import SSEFormatter
from shared.debug_utils import debug_log

router = APIRouter()

# 延迟创建 orchestrator
_orchestrator = None

def get_orchestrator():
    """获取 Orchestrator 实例（单例模式）"""
    global _orchestrator
    if _orchestrator is None:
        try:
            _orchestrator = Orchestrator()
        except Exception as e:
            debug_log(
                f"Failed to initialize Orchestrator: {str(e)}",
                level="error"
            )
            raise
    return _orchestrator

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # 会话 ID（可选）

@router.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求（非流式）"""
    try:
        debug_log(
            "收到聊天请求",
            data={
                "message_preview": request.message[:50] if request.message else None,
                "session_id": request.session_id
            }
        )
        orchestrator = get_orchestrator()
        context = {}
        if request.session_id:
            context["session_id"] = request.session_id
        
        debug_log("开始处理请求...")
        response = await orchestrator.process(request.message, context=context)
        debug_log(
            "请求处理成功",
            data={"response_length": len(response) if response else 0}
        )
        
        # 返回响应和会话 ID（如果是新会话）
        result = {
            "response": response,
            "status": "success"
        }
        if not request.session_id:
            # 如果是新会话，返回会话 ID（需要从 orchestrator 获取）
            # 简化处理：前端可以自己管理会话 ID
            pass
        
        return result
    except Exception as e:
        error_trace = traceback.format_exc()
        debug_log(
            f"Chat request failed: {str(e)}",
            level="error",
            data={"error_trace": error_trace}
        )
        # 返回 200 状态码，但在响应中包含错误信息
        # 这样前端可以正常处理，而不是收到 502
        return {
            "response": None,
            "status": "error",
            "error": str(e)
        }

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """处理聊天请求（流式 SSE）"""
    import traceback
    from fastapi.responses import StreamingResponse
    
    debug_log(
        "chat_stream路由被调用",
        data={
            "message_preview": request.message[:50] if request.message else None,
            "session_id": request.session_id
        }
    )
    
    async def generate():
        try:
            orchestrator = get_orchestrator()
            context = {}
            if request.session_id:
                context["session_id"] = request.session_id
            
            debug_log("开始流式处理请求...")
            
            # 使用 SSE 格式发送流式响应
            formatter = SSEFormatter()
            
            async for chunk in orchestrator.stream_process(request.message, context=context):
                if chunk:
                    yield formatter.format_chunk(chunk, "streaming")
            
            # 发送结束标记
            yield formatter.format_done()
            
            debug_log("流式响应完成")
        except Exception as e:
            error_trace = traceback.format_exc()
            debug_log(
                f"Stream chat request failed: {str(e)}",
                level="error",
                data={"error_trace": error_trace}
            )
            # 发送错误信息
            formatter = SSEFormatter()
            yield formatter.format_error(str(e))
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "Transfer-Encoding": "chunked"
        }
    )

