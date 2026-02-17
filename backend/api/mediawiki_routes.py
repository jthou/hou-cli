"""MediaWiki 相关路由"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.mediawiki_client_service import (
    MediaWikiClientService,
    MediaWikiSyncService
)
from shared.debug_utils import debug_log

router = APIRouter()

# 延迟创建服务实例
_mediawiki_client = None
_mediawiki_sync_service = None

def get_mediawiki_client():
    """获取 MediaWiki 客户端实例（单例模式）"""
    global _mediawiki_client
    if _mediawiki_client is None:
        try:
            _mediawiki_client = MediaWikiClientService()
            _mediawiki_client.connect()
        except Exception as e:
            debug_log(
                f"Failed to initialize MediaWiki client: {str(e)}",
                level="error"
            )
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
            debug_log(
                f"Failed to initialize MediaWiki sync service: {str(e)}",
                level="error"
            )
            raise
    return _mediawiki_sync_service

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
    try:
        if limit < 1 or limit > 100:
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
    except HTTPException:
        # 重新抛出 HTTPException（如参数验证错误）
        raise
    except Exception as e:
        debug_log(
            f"MediaWiki search failed: {str(e)}",
            level="error"
        )
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
    try:
        client = get_mediawiki_client()
        page = client.get_page(title)
        
        if not page:
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
    except HTTPException:
        # 重新抛出 HTTPException（如404错误）
        raise
    except Exception as e:
        debug_log(
            f"Get MediaWiki page failed: {str(e)}",
            level="error"
        )
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
            raise HTTPException(
                status_code=500,
                detail="Edit failed"
            )
    except Exception as e:
        debug_log(
            f"Edit MediaWiki page failed: {str(e)}",
            level="error"
        )
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
        debug_log(
            f"MediaWiki sync failed: {str(e)}",
            level="error"
        )
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
    try:
        sync_service = get_mediawiki_sync_service()
        status = sync_service.get_sync_status()
        
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        debug_log(
            f"Get sync status failed: {str(e)}",
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync status: {str(e)}"
        )

