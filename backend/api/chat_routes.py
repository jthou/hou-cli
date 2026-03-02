"""聊天相关路由"""
import traceback
from typing import List, Optional
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
    current_article: Optional[str] = None  # 写文章时右侧草稿，会注入对话上下文并持久化
    context_type: Optional[str] = None  # 建新会话时的类型，如 article_writing；无 session_id 时生效

@router.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求（非流式）"""
    try:
        debug_log(
            "收到聊天请求",
            data={
                "message_preview": request.message[:50] if request.message else None,
                "session_id": request.session_id,
                "has_current_article": request.current_article is not None,
            }
        )
        orchestrator = get_orchestrator()
        context = {}
        if request.session_id:
            context["session_id"] = request.session_id
        if request.context_type:
            context["context_type"] = request.context_type
        # 写文章：保存右侧草稿，供本次及后续轮次注入上下文
        if request.session_id and request.current_article is not None:
            orchestrator.context_manager.set_current_article(
                request.session_id, request.current_article
            )

        debug_log("开始处理请求...")
        response = await orchestrator.process(request.message, context=context)
        debug_log(
            "请求处理成功",
            data={"response_length": len(response) if response else 0}
        )

        # 返回响应与当前文章（右侧预览用）
        result = {
            "response": response,
            "status": "success",
        }
        if request.session_id:
            article = orchestrator.context_manager.get_current_article(
                request.session_id
            )
            if article is not None:
                result["article"] = article
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
            if request.context_type:
                context["context_type"] = request.context_type
            # 写文章：保存右侧草稿供流式分支注入上下文（与 POST /chat 一致）
            if request.session_id and request.current_article is not None:
                orchestrator.context_manager.set_current_article(
                    request.session_id, request.current_article
                )
            
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


@router.get("/chat/article")
async def get_chat_article(session_id: Optional[str] = None):
    """获取写文章会话的当前文章草稿（右侧预览），用于恢复页面时加载。"""
    if not session_id:
        return {"article": None, "status": "success"}
    try:
        orchestrator = get_orchestrator()
        article = orchestrator.context_manager.get_current_article(session_id)
        return {"article": article, "status": "success"}
    except Exception as e:
        debug_log(f"get_chat_article failed: {e}", level="error")
        return {"article": None, "status": "error", "error": str(e)}


class MwSourcesRequest(BaseModel):
    session_id: str
    titles: List[str] = []


@router.get("/chat/mw-sources")
async def get_chat_mw_sources(session_id: Optional[str] = None):
    """获取写文章会话的参考 MediaWiki 页面标题列表。"""
    if not session_id:
        return {"titles": [], "status": "success"}
    try:
        orchestrator = get_orchestrator()
        titles = orchestrator.context_manager.get_mw_source_titles(session_id)
        return {"titles": titles, "status": "success"}
    except Exception as e:
        debug_log(f"get_chat_mw_sources failed: {e}", level="error")
        return {"titles": [], "status": "error", "error": str(e)}


@router.put("/chat/mw-sources")
async def put_chat_mw_sources(request: MwSourcesRequest):
    """设置写文章会话的参考 MediaWiki 页面标题列表（覆盖）。"""
    try:
        orchestrator = get_orchestrator()
        ok = orchestrator.context_manager.set_mw_source_titles(
            request.session_id, request.titles or []
        )
        return {"status": "success" if ok else "error", "success": ok}
    except Exception as e:
        debug_log(f"put_chat_mw_sources failed: {e}", level="error")
        return {"status": "error", "success": False, "error": str(e)}


class SetArticleRequest(BaseModel):
    session_id: str
    content: str


@router.put("/chat/article")
async def set_chat_article(request: SetArticleRequest):
    """将指定内容设为当前会话的文章草稿（用于「写入右侧预览」）。"""
    if not request.session_id:
        return {"article": None, "status": "error", "error": "缺少 session_id"}
    try:
        orchestrator = get_orchestrator()
        ok = orchestrator.context_manager.set_current_article(
            request.session_id, request.content or ""
        )
        article = orchestrator.context_manager.get_current_article(request.session_id) if ok else None
        return {"article": article, "status": "success" if ok else "error", "success": ok}
    except Exception as e:
        debug_log(f"set_chat_article failed: {e}", level="error")
        return {"article": None, "status": "error", "success": False, "error": str(e)}

