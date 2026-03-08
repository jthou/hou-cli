"""MediaWiki 相关路由"""
from typing import Optional
import random

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.mediawiki_client_service import (
    MediaWikiClientService,
    MediaWikiSyncService,
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
    limit: int = 20,
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
            detail=f"Search failed: {str(e)}",
        )


@router.get("/mediawiki/search-read")
async def search_and_read_mediawiki(
    terms: str,
    per_term_limit: int = 5,
):
    """
    按多个关键词搜索 MediaWiki，并读取每篇页面的完整内容。

    - terms: 用逗号或空格分隔的多个关键词，例如
      "网文抓取, hou-cli, 2026年3月3日, 2026年第10周, 2026年3月"
    - per_term_limit: 每个关键词最多抓取的文章数，默认 5，范围 1–20。
    """
    try:
        raw_terms = terms or ""
        parts = [
            p.strip()
            for p in raw_terms.replace("，", ",").split(",")
            if p.strip()
        ]
        # 允许用户用空格分词；如果只给了一个长串，再按空白拆一层
        if len(parts) == 1:
            parts = [p.strip() for p in raw_terms.split() if p.strip()]

        uniq_terms = []
        seen = set()
        for p in parts:
            if p and p not in seen:
                seen.add(p)
                uniq_terms.append(p)

        if not uniq_terms:
            raise HTTPException(
                status_code=400,
                detail=(
                    "terms 参数解析失败：请提供至少一个非空关键词"
                    "（用逗号或空格分隔）。"
                ),
            )

        try:
            per_term = int(per_term_limit)
        except (TypeError, ValueError):
            per_term = 5
        if per_term < 1:
            per_term = 1
        if per_term > 20:
            per_term = 20

        client = get_mediawiki_client()

        results = []
        total_pages = 0

        for term in uniq_terms:
            search_results = client.search_pages(term, limit=per_term)
            pages = []
            for r in search_results:
                page = client.get_page(r.title)
                if not page:
                    continue
                pages.append(
                    {
                        "title": page.title,
                        "url": page.url,
                        "categories": page.categories,
                        "content": page.content,
                    }
                )

            results.append(
                {
                    "term": term,
                    "requested_limit": per_term,
                    "count": len(pages),
                    "pages": pages,
                }
            )
            total_pages += len(pages)

        return {
            "success": True,
            "terms": uniq_terms,
            "per_term_limit": per_term,
            "total_pages": total_pages,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(
            f"MediaWiki search-read failed: {str(e)}",
            level="error",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Search-read failed: {str(e)}",
        )


@router.get("/mediawiki/recent-read")
async def recent_read_mediawiki(
    count: int = 10,
):
    """
    获取最近修改的 n 篇 MediaWiki 文章的完整内容。

    - count: 文章数量，默认 10，范围 1–50。
    """
    try:
        try:
            n = int(count)
        except (TypeError, ValueError):
            n = 10
        if n < 1:
            n = 1
        if n > 50:
            n = 50

        client = get_mediawiki_client()
        titles = client.get_recently_changed_pages(limit=n, namespace=0)
        if not titles:
            raise HTTPException(
                status_code=404,
                detail="MediaWiki 中暂无最近修改的页面。",
            )

        pages = []
        for title in titles:
            page = client.get_page(title)
            if not page:
                continue
            pages.append(
                {
                    "title": page.title,
                    "url": page.url,
                    "categories": page.categories,
                    "content": page.content,
                }
            )

        results = [
            {
                "term": "最新更改",
                "requested_limit": n,
                "count": len(pages),
                "pages": pages,
            }
        ]

        return {
            "success": True,
            "terms": ["最新更改"],
            "per_term_limit": n,
            "total_pages": len(pages),
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(
            f"MediaWiki recent-read failed: {str(e)}",
            level="error",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Recent-read failed: {str(e)}",
        )


@router.get("/mediawiki/random-read")
async def random_read_mediawiki(
    count: int = 5,
):
    """
    随机抓取若干篇 MediaWiki 文章的完整内容。

    - count: 随机抓取的文章数量，默认 5，范围 1–50。
    """
    try:
        try:
            n = int(count)
        except (TypeError, ValueError):
            n = 5
        if n < 1:
            n = 1
        if n > 50:
            n = 50

        client = get_mediawiki_client()
        titles = client.get_all_pages(namespace=0, limit=None)
        total_titles = len(titles)
        if total_titles == 0:
            raise HTTPException(
                status_code=404,
                detail="MediaWiki 中暂无页面可供随机抓取。",
            )

        if n >= total_titles:
            sample_titles = titles
        else:
            sample_titles = random.sample(titles, n)

        pages = []
        for title in sample_titles:
            page = client.get_page(title)
            if not page:
                continue
            pages.append(
                {
                    "title": page.title,
                    "url": page.url,
                    "categories": page.categories,
                    "content": page.content,
                }
            )

        results = [
            {
                "term": "随机",
                "requested_limit": n,
                "count": len(pages),
                "pages": pages,
            }
        ]

        return {
            "success": True,
            "terms": ["随机"],
            "per_term_limit": n,
            "total_pages": len(pages),
            "wiki_total_titles": total_titles,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(
            f"MediaWiki random-read failed: {str(e)}",
            level="error",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Random-read failed: {str(e)}",
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

