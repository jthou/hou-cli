"""Wikipedia 阅读 API 路由（与 MediaWiki 相同接口结构）"""
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.wikipedia_mediawiki_client import (
    search_pages as wp_search,
    get_page_content,
    parse_wikitext,
    get_random_titles,
    get_recently_changed_titles,
    _get_base_url,
)

router = APIRouter()


@router.get("/wikipedia/diagnostic")
async def wikipedia_diagnostic():
    """诊断 Wikipedia API 是否已加载（用于排查 404：需重启后端以加载新路由）"""
    return {"ok": True, "message": "Wikipedia API 已加载"}


def _make_wiki_links_absolute(html: str, base_url: str) -> str:
    """将 parse 返回的 HTML 中相对 wiki 链接转为绝对 URL。"""
    if not base_url or not html:
        return html
    base = base_url.rstrip("/")
    html = re.sub(r'href="/index\.php/', f'href="{base}/index.php/', html)
    html = re.sub(r'href="/wiki/', f'href="{base}/wiki/', html)
    return html


@router.get("/wikipedia/search-read")
async def wikipedia_search_read(
    terms: str,
    per_term_limit: int = 5,
    lang: str = "zh",
):
    """
    按多个关键词搜索 Wikipedia，并读取每篇页面的完整内容。
    与 MediaWiki search-read 结构一致。
    """
    try:
        raw_terms = terms or ""
        parts = [
            p.strip()
            for p in raw_terms.replace("，", ",").split(",")
            if p.strip()
        ]
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
                detail="terms 参数解析失败：请提供至少一个非空关键词",
            )
        per_term = max(1, min(20, int(per_term_limit) if per_term_limit else 5))
        results = []
        total_pages = 0
        for term in uniq_terms:
            hits = wp_search(term, limit=per_term, lang=lang)
            pages = []
            for r in hits:
                page = get_page_content(r["title"], lang=lang)
                if not page:
                    continue
                pages.append({
                    "title": page["title"],
                    "url": page["url"],
                    "categories": page.get("categories", []),
                    "content": page["content"],
                })
            results.append({
                "term": term,
                "requested_limit": per_term,
                "count": len(pages),
                "pages": pages,
            })
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wikipedia/recent-read")
async def wikipedia_recent_read(count: int = 10, lang: str = "zh"):
    """获取最近修改的 n 篇 Wikipedia 文章。"""
    try:
        n = max(1, min(50, int(count) if count else 10))
        titles = get_recently_changed_titles(limit=n, lang=lang)
        pages = []
        for title in titles:
            page = get_page_content(title, lang=lang)
            if not page:
                continue
            pages.append({
                "title": page["title"],
                "url": page["url"],
                "categories": page.get("categories", []),
                "content": page["content"],
            })
        return {
            "success": True,
            "terms": ["最新更改"],
            "per_term_limit": n,
            "total_pages": len(pages),
            "results": [{
                "term": "最新更改",
                "requested_limit": n,
                "count": len(pages),
                "pages": pages,
            }],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wikipedia/random-read")
async def wikipedia_random_read(count: int = 5, lang: str = "zh"):
    """随机抓取若干篇 Wikipedia 文章。"""
    try:
        n = max(1, min(20, int(count) if count else 5))
        titles = get_random_titles(limit=n, lang=lang)
        pages = []
        for title in titles:
            page = get_page_content(title, lang=lang)
            if not page:
                continue
            pages.append({
                "title": page["title"],
                "url": page["url"],
                "categories": page.get("categories", []),
                "content": page["content"],
            })
        return {
            "success": True,
            "terms": ["随机"],
            "per_term_limit": n,
            "total_pages": len(pages),
            "results": [{
                "term": "随机",
                "requested_limit": n,
                "count": len(pages),
                "pages": pages,
            }],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wikipedia/pages/{title:path}")
async def wikipedia_get_page(title: str, lang: str = "zh"):
    """获取 Wikipedia 页面内容。"""
    try:
        page = get_page_content(title, lang=lang)
        if not page:
            raise HTTPException(status_code=404, detail=f"Page '{title}' not found")
        return {
            "success": True,
            "page": {
                "title": page["title"],
                "content": page["content"],
                "url": page["url"],
                "categories": page.get("categories", []),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class WikipediaParseRequest(BaseModel):
    wikitext: str
    title: Optional[str] = None
    lang: str = "zh"


@router.post("/wikipedia/parse")
async def wikipedia_parse(req: WikipediaParseRequest):
    """Wikipedia wikitext 转 HTML 预览。"""
    try:
        html = parse_wikitext(req.wikitext, title=req.title, lang=req.lang)
        base_url = _get_base_url(req.lang)
        html = _make_wiki_links_absolute(html, base_url)
        return {"success": True, "html": html, "base_url": base_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wikipedia/base-url")
async def wikipedia_base_url(lang: str = "zh"):
    """返回 Wikipedia 基础 URL。"""
    return {"base_url": _get_base_url(lang)}
