"""搜索相关路由"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from backend.services.file_search_service.file_search_service import FileSearchService
from backend.services.file_search_service.models import FileSearchRequest, FileSearchResponse
from backend.services.mediawiki_client_service import UnifiedSearchService
from shared.debug_utils import debug_log

router = APIRouter()

# 延迟创建搜索服务
_search_service = None
_unified_search_service = None

def get_search_service():
    """获取 FileSearchService 实例（单例模式）"""
    global _search_service
    if _search_service is None:
        try:
            _search_service = FileSearchService()
        except Exception as e:
            debug_log(
                f"Failed to initialize FileSearchService: {str(e)}",
                level="error"
            )
            raise
    return _search_service

def get_unified_search_service():
    """获取统一搜索服务实例（单例模式）"""
    global _unified_search_service
    if _unified_search_service is None:
        try:
            from backend.services.mediawiki_client_service import MediaWikiClientService
            client = MediaWikiClientService()
            client.connect()
            _unified_search_service = UnifiedSearchService(mediawiki_client=client)
        except Exception as e:
            debug_log(
                f"Failed to initialize unified search service: {str(e)}",
                level="error"
            )
            raise
    return _unified_search_service

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
    try:
        # 验证参数
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="limit must be between 1 and 1000"
            )
        
        if offset < 0:
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
        
    except HTTPException:
        # 重新抛出 HTTPException（如参数验证错误）
        raise
    except Exception as e:
        debug_log(
            f"File search failed: {str(e)}",
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/search/availability")
async def check_search_availability():
    """检查搜索功能可用性"""
    try:
        search_service = get_search_service()
        available, error = search_service.check_availability()
        
        return {
            "success": True,
            "available": available,
            "error": error
        }
    except Exception as e:
        debug_log(
            f"检查搜索可用性失败: {str(e)}",
            level="error"
        )
        return {
            "success": False,
            "available": False,
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
    try:
        if limit < 1 or limit > 100:
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
    except HTTPException:
        # 重新抛出 HTTPException（如参数验证错误）
        raise
    except Exception as e:
        debug_log(
            f"Unified search failed: {str(e)}",
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

