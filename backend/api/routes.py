"""路由定义"""
import os
import json
import asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 加载 .env 文件（在导入 Orchestrator 之前）
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

from backend.core.agent.orchestrator import Orchestrator
from backend.services.search.file_search_service import FileSearchService
from backend.services.search.models import FileSearchRequest
from backend.api.stream_sender import StreamSender

router = APIRouter()

# 延迟创建搜索服务
_search_service = None

def get_search_service():
    """获取 FileSearchService 实例（单例模式）"""
    global _search_service
    if _search_service is None:
        try:
            _search_service = FileSearchService()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize FileSearchService: {str(e)}", exc_info=True)
            raise
    return _search_service

# 延迟创建 orchestrator，确保 .env 已加载
_orchestrator = None

def get_orchestrator():
    """获取 Orchestrator 实例（单例模式）"""
    global _orchestrator
    if _orchestrator is None:
        try:
            _orchestrator = Orchestrator()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize Orchestrator: {str(e)}", exc_info=True)
            raise
    return _orchestrator

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # 会话 ID（可选）

@router.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求（非流式）"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug(f"收到聊天请求: message={request.message[:50]}..., session_id={request.session_id}")
        orchestrator = get_orchestrator()
        context = {}
        if request.session_id:
            context["session_id"] = request.session_id
        
        logger.debug("开始处理请求...")
        response = await orchestrator.process(request.message, context=context)
        logger.debug(f"请求处理成功，响应长度: {len(response) if response else 0}")
        
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
        logger.error(f"Chat request failed: {str(e)}\n{error_trace}")
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
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    async def generate():
        try:
            logger.debug(f"收到流式聊天请求: message={request.message[:50]}..., session_id={request.session_id}")
            # 立即发送一个心跳，保持连接活跃
            yield await StreamSender.send_chunk("", "streaming")
            
            orchestrator = get_orchestrator()
            context = {}
            if request.session_id:
                context["session_id"] = request.session_id
            
            logger.debug("开始流式处理请求...")
            try:
                async for chunk in orchestrator.stream_process(request.message, context=context):
                    try:
                        # 使用 StreamSender 发送数据块
                        yield await StreamSender.send_chunk(chunk, "streaming")
                    except Exception as chunk_error:
                        # 单个 chunk 处理失败，记录但继续
                        logger.warning(f"处理 chunk 时出错: {str(chunk_error)}")
                        continue
                # 发送完成信号
                logger.debug("流式处理完成")
                yield await StreamSender.send_done()
            except GeneratorExit:
                # 客户端断开连接，正常情况
                logger.debug("客户端断开连接")
                raise
            except asyncio.CancelledError:
                # 任务被取消，正常情况
                logger.debug("流式处理被取消")
                raise
            except Exception as inner_e:
                # 流式处理过程中的异常
                error_trace = traceback.format_exc()
                logger.error(f"流式处理过程中出错: {str(inner_e)}\n{error_trace}")
                try:
                    # 发送错误信号
                    yield await StreamSender.send_error(str(inner_e))
                except Exception:
                    # 如果发送错误信号也失败，记录日志
                    logger.error("无法发送错误信号，连接可能已关闭")
        except Exception as e:
            # 外层异常（如 orchestrator 初始化失败）
            error_trace = traceback.format_exc()
            logger.error(f"流式聊天请求失败: {str(e)}\n{error_trace}")
            # 发送错误信号
            yield await StreamSender.send_error(str(e))
    
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

@router.get("/sessions/list")
async def list_sessions(limit: int = 10):
    """列出最近的会话"""
    try:
        orchestrator = get_orchestrator()
        sessions = orchestrator.context_manager.list_sessions(limit=limit)
        
        # 获取每个会话的预览信息
        result = []
        for session in sessions:
            try:
                preview = orchestrator.context_manager.get_session_preview(session.session_id)
                result.append(preview)
            except Exception as e:
                # 如果获取预览失败，使用基本信息
                result.append({
                    "session_id": session.session_id,
                    "preview": "",
                    "message_count": 0,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "metadata": session.metadata
                })
        
        return {"sessions": result}
    except Exception as e:
        return {
            "sessions": [],
            "error": str(e)
        }

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.context_manager.clear_session(session_id)
        
        if result:
            return {"success": True, "message": f"会话 {session_id} 已删除"}
        else:
            return {"success": False, "error": f"会话不存在或删除失败: {session_id}"}
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/sessions/{session_id}/clear")
async def clear_session_messages(session_id: str):
    """清除会话的所有消息"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        logger.debug(f"清除会话消息: session_id={session_id}")
        orchestrator = get_orchestrator()
        result = orchestrator.context_manager.clear_session(session_id)
        
        if result:
            logger.debug(f"成功清除会话消息: session_id={session_id}")
            return {"success": True, "message": f"会话 {session_id} 的消息已清除"}
        else:
            logger.warning(f"清除会话消息失败: session_id={session_id}")
            return {"success": False, "error": f"会话不存在或清除失败: {session_id}"}
    except Exception as e:
        logger.error(f"清除会话消息异常: session_id={session_id}, 错误: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """获取会话详情（包含消息列表）"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        logger.debug(f"获取会话详情: session_id={session_id}")
        orchestrator = get_orchestrator()
        session = orchestrator.context_manager.get_session(session_id)
        
        if not session:
            logger.warning(f"会话不存在: {session_id}")
            return {"success": False, "error": f"会话不存在: {session_id}"}
        
        # 获取消息列表（不压缩，用于显示）
        logger.debug(f"获取消息列表: session_id={session_id}, compressed=False")
        messages = orchestrator.context_manager.get_messages(
            session_id,
            compressed=False
        )
        logger.debug(f"获取到 {len(messages)} 条消息")
        
        # 转换为字典格式
        messages_data = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "message_id": msg.message_id
            }
            for msg in messages
        ]
        
        result = {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata
            },
            "messages": messages_data
        }
        logger.debug(f"成功获取会话详情: session_id={session_id}, messages_count={len(messages_data)}")
        return result
    except Exception as e:
        logger.error(f"获取会话详情失败: session_id={session_id}, 错误: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/sessions/search")
async def search_sessions(keyword: str, limit: int = 10):
    """搜索包含关键词的会话"""
    try:
        orchestrator = get_orchestrator()
        all_sessions = orchestrator.context_manager.list_sessions(limit=1000)
        
        # 搜索匹配的会话
        matching_sessions = []
        for session in all_sessions:
            # 获取会话预览
            try:
                preview = orchestrator.context_manager.get_session_preview(session.session_id)
                # 检查预览文本、会话 ID 或元数据中是否包含关键词
                if (keyword.lower() in preview.get("preview", "").lower() or
                    keyword.lower() in session.session_id.lower() or
                    any(keyword.lower() in str(v).lower() for v in session.metadata.values() if v)):
                    matching_sessions.append(preview)
            except:
                continue
            
            if len(matching_sessions) >= limit:
                break
        
        return {"sessions": matching_sessions}
    except Exception as e:
        return {
            "sessions": [],
            "error": str(e)
        }

@router.post("/sessions")
async def create_session():
    """创建新会话"""
    try:
        orchestrator = get_orchestrator()
        session_id = orchestrator.context_manager.create_session()
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"新会话已创建: {session_id}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/sessions/{session_id}/summary")
async def generate_session_summary(session_id: str):
    """生成会话摘要"""
    try:
        orchestrator = get_orchestrator()
        session = orchestrator.context_manager.get_session(session_id)
        
        if not session:
            return {"success": False, "error": f"会话不存在: {session_id}"}
        
        # 获取消息列表
        messages = orchestrator.context_manager.get_messages(session_id, compressed=False)
        
        if not messages:
            return {"success": False, "error": "会话中没有消息"}
        
        # 构建对话内容用于摘要生成
        conversation_text = "\n".join([
            f"{msg.role.value}: {msg.content}"
            for msg in messages
        ])
        
        # 使用 LLM 生成摘要
        system_prompt = "你是一个专业的对话摘要生成器。请为以下对话生成一个简洁、准确的摘要，包括主要话题、关键信息和结论。"
        user_prompt = f"请为以下对话生成摘要：\n\n{conversation_text}"
        
        summary = await orchestrator.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "success": True,
            "summary": summary,
            "session_id": session_id,
            "message_count": len(messages)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# 文件搜索 API
from backend.services.search.file_search_service import FileSearchService
from backend.services.search.models import FileSearchRequest, FileSearchResponse

_search_service = None

def get_search_service():
    """获取 FileSearchService 实例（单例模式）"""
    global _search_service
    if _search_service is None:
        try:
            _search_service = FileSearchService()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize FileSearchService: {str(e)}", exc_info=True)
            raise
    return _search_service

@router.get("/search/files", response_model=FileSearchResponse)
async def search_files(
    query: str,
    path: Optional[str] = None,
    file_type: Optional[str] = None,
    content_search: bool = False,
    limit: int = 100,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: str = "asc"
):
    """文件搜索 API
    
    Args:
        query: 搜索关键词
        path: 搜索路径限制（可选）
        file_type: 文件类型过滤（可选，如 '*.py'）
        content_search: 是否进行文件内容搜索
        limit: 结果数量限制（默认 100，最大 1000）
        offset: 分页偏移量
        sort_by: 排序字段（name, size, modified_time）
        sort_order: 排序顺序（asc, desc）
        
    Returns:
        FileSearchResponse: 搜索结果响应
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 验证参数
        if limit < 1 or limit > 1000:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="limit must be between 1 and 1000"
            )
        
        if offset < 0:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="offset must be >= 0"
            )
        
        # 创建搜索请求
        request = FileSearchRequest(
            query=query,
            path=path,
            file_type=file_type,
            content_search=content_search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 执行搜索
        service = get_search_service()
        response = service.search(request)
        
        return response
        
    except Exception as e:
        logger.error(f"File search failed: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/search/availability")
async def check_search_availability():
    """检查搜索功能可用性"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        search_service = get_search_service()
        available, error = search_service.check_availability()
        
        return {
            "success": True,
            "available": available,
            "error": error
        }
    except Exception as e:
        logger.error(f"检查搜索可用性失败: {e}", exc_info=True)
        return {
            "success": False,
            "available": False,
            "error": str(e)
        }

# MediaWiki API
from backend.services.mediawiki import (
    MediaWikiClientService,
    MediaWikiSyncService,
    UnifiedSearchService
)
from backend.services.mediawiki.models import MediaWikiPage, UnifiedSearchResult

_mediawiki_client = None
_mediawiki_sync_service = None
_unified_search_service = None

def get_mediawiki_client():
    """获取 MediaWiki 客户端实例（单例模式）"""
    global _mediawiki_client
    if _mediawiki_client is None:
        try:
            _mediawiki_client = MediaWikiClientService()
            _mediawiki_client.connect()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize MediaWiki client: {str(e)}", exc_info=True)
            raise
    return _mediawiki_client

def get_mediawiki_sync_service():
    """获取 MediaWiki 同步服务实例（单例模式）"""
    global _mediawiki_sync_service
    if _mediawiki_sync_service is None:
        try:
            client = get_mediawiki_client()
            _mediawiki_sync_service = MediaWikiSyncService(client=client)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize MediaWiki sync service: {str(e)}", exc_info=True)
            raise
    return _mediawiki_sync_service

def get_unified_search_service():
    """获取统一搜索服务实例（单例模式）"""
    global _unified_search_service
    if _unified_search_service is None:
        try:
            client = get_mediawiki_client()
            _unified_search_service = UnifiedSearchService(mediawiki_client=client)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize unified search service: {str(e)}", exc_info=True)
            raise
    return _unified_search_service

class MediaWikiEditRequest(BaseModel):
    """MediaWiki 编辑请求"""
    content: str
    summary: Optional[str] = ""

@router.get("/mediawiki/search")
async def search_mediawiki(
    query: str,
    limit: int = 20
):
    """搜索 MediaWiki 页面
    
    Args:
        query: 搜索关键词
        limit: 结果数量限制（默认 20，最大 100）
        
    Returns:
        搜索结果列表
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        if limit < 1 or limit > 100:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="limit must be between 1 and 100"
            )
        
        client = get_mediawiki_client()
        results = client.search_pages(query, limit=limit)
        
        return {
            "success": True,
            "count": len(results),
            "results": [
                {
                    "title": r.title,
                    "snippet": r.snippet,
                    "url": r.url,
                    "score": r.score
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"MediaWiki search failed: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/mediawiki/pages/{title:path}")
async def get_mediawiki_page(title: str):
    """获取 MediaWiki 页面
    
    Args:
        title: 页面标题（URL 编码）
        
    Returns:
        页面内容
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        client = get_mediawiki_client()
        page = client.get_page(title)
        
        if not page:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail=f"Page '{title}' not found"
            )
        
        return {
            "success": True,
            "page": {
                "title": page.title,
                "content": page.content,
                "url": page.url,
                "categories": page.categories,
                "links": page.links,
                "last_modified": page.last_modified.isoformat(),
                "revision_id": page.revision_id
            }
        }
    except Exception as e:
        logger.error(f"Get MediaWiki page failed: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get page: {str(e)}"
        )

@router.post("/mediawiki/pages/{title:path}")
async def edit_mediawiki_page(title: str, request: MediaWikiEditRequest):
    """编辑 MediaWiki 页面
    
    Args:
        title: 页面标题（URL 编码）
        request: 编辑请求（包含 content 和 summary）
        
    Returns:
        编辑结果
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        client = get_mediawiki_client()
        success = client.edit_page(
            title,
            request.content,
            summary=request.summary or "由 API 编辑"
        )
        
        if success:
            return {
                "success": True,
                "message": f"Page '{title}' edited successfully"
            }
        else:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail="Edit failed"
            )
    except Exception as e:
        logger.error(f"Edit MediaWiki page failed: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Edit failed: {str(e)}"
        )

@router.post("/mediawiki/sync")
async def trigger_sync(
    force: bool = False,
    category: Optional[str] = None
):
    """触发 MediaWiki 同步
    
    Args:
        force: 是否强制全量同步
        category: 同步指定分类（可选）
        
    Returns:
        同步结果
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        sync_service = get_mediawiki_sync_service()
        
        if category:
            result = sync_service.sync_category(category, force=force)
        else:
            result = sync_service.sync_all_pages(force=force)
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"MediaWiki sync failed: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )

@router.get("/mediawiki/sync/status")
async def get_sync_status():
    """获取同步状态
    
    Returns:
        同步状态信息
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        sync_service = get_mediawiki_sync_service()
        status = sync_service.get_sync_status()
        
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        logger.error(f"Get sync status failed: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync status: {str(e)}"
        )

@router.get("/tools/list")
async def list_tools():
    """获取可用工具列表"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        orchestrator = get_orchestrator()
        # 获取工具对象（不是名称列表）
        tool_registry = orchestrator.tool_registry
        tools = tool_registry._tools.values()  # 直接访问工具字典
        
        tools_info = []
        for tool in tools:
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)
            tool_desc = tool.description if hasattr(tool, 'description') else ""
            
            # 如果描述为空，尝试从工具类获取
            if not tool_desc and hasattr(tool, '__class__'):
                # 尝试获取类的文档字符串
                if tool.__class__.__doc__:
                    tool_desc = tool.__class__.__doc__.strip().split('\n')[0]
            
            # 如果还是没有描述，使用默认描述
            if not tool_desc:
                tool_desc = f"{tool_name} 工具"
            
            # 只取第一行描述（去掉换行和多余空格）
            tool_desc = tool_desc.split('\n')[0].strip()
            
            tool_info = {
                "name": tool_name,
                "description": tool_desc
            }
            tools_info.append(tool_info)
        
        return {
            "success": True,
            "tools": tools_info,
            "count": len(tools_info)
        }
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/search/unified")
async def unified_search(
    query: str,
    limit: int = 20,
    sources: Optional[str] = None
):
    """统一搜索（MediaWiki + 知识库）
    
    Args:
        query: 搜索关键词
        limit: 结果数量限制
        sources: 搜索来源，逗号分隔（"mediawiki,knowledge_base"），None 表示搜索所有来源
        
    Returns:
        合并后的搜索结果
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        if limit < 1 or limit > 100:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="limit must be between 1 and 100"
            )
        
        source_list = None
        if sources:
            source_list = [s.strip() for s in sources.split(",")]
        
        search_service = get_unified_search_service()
        results = search_service.search(query, limit=limit, sources=source_list)
        
        return {
            "success": True,
            "count": len(results),
            "results": [
                {
                    "source": r.source,
                    "title": r.title,
                    "content": r.content,
                    "score": r.score,
                    "url": r.url,
                    "metadata": r.metadata
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Unified search failed: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

