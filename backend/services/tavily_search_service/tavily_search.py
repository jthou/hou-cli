"""
Tavily 搜索服务：通过 Tavily API 执行搜索，返回与 GoogleSearchResponse 兼容的结构。
需 TAVILY_API_KEY，每月 1000 次免费额度，调用次数纳入审计。
"""
import logging
import os
import time
from typing import List, Optional
from urllib.parse import urlparse

from backend.services.google_search_service.models import GoogleSearchResult, GoogleSearchResponse
from .tavily_usage_audit import append_tavily_audit

logger = logging.getLogger(__name__)


class TavilySearchError(Exception):
    """Tavily 搜索错误"""
    pass


def _credits_for_depth(search_depth: str) -> int:
    """basic=1, advanced=2"""
    return 2 if (search_depth or "").lower() == "advanced" else 1


def search(
    query: str,
    num_results: int = 10,
    language: Optional[str] = None,
    search_depth: str = "basic",
    timeout: float = 30.0,
) -> GoogleSearchResponse:
    """
    使用 Tavily API 执行搜索，返回与 GoogleSearchResponse 兼容的结构。

    Args:
        query: 搜索查询
        num_results: 返回结果数量（1-20，Tavily 限制）
        language: 语言代码（可选，Tavily 暂不直接支持，保留兼容）
        search_depth: "basic"（1 credit）或 "advanced"（2 credits）
        timeout: 超时秒数

    Returns:
        GoogleSearchResponse

    Raises:
        TavilySearchError: API 调用失败时
    """
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise TavilySearchError("TAVILY_API_KEY 未设置")

    num_results = max(1, min(20, num_results))
    search_depth = (search_depth or "basic").lower()
    if search_depth not in ("basic", "advanced"):
        search_depth = "basic"
    credits = _credits_for_depth(search_depth)

    start = time.time()
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        raw = client.search(
            query=query,
            search_depth=search_depth,
            max_results=num_results,
        )
    except ImportError as e:
        raise TavilySearchError(f"tavily-python 未安装: {e}") from e
    except Exception as e:
        msg = str(e).strip() or getattr(e, "__class__", type(e)).__name__
        raise TavilySearchError(f"Tavily API 调用失败: {msg}") from e

    response_time = time.time() - start

    # Tavily 返回 dict: results=[{title, url, content, score}], query, response_time
    raw_results = raw.get("results", []) if isinstance(raw, dict) else (getattr(raw, "results", []) or [])
    results: List[GoogleSearchResult] = []
    for r in raw_results:
        title = getattr(r, "title", None) or getattr(r, "name", None) or ""
        url = getattr(r, "url", None) or getattr(r, "link", None) or ""
        content = getattr(r, "content", None) or getattr(r, "snippet", None) or ""
        if isinstance(r, dict):
            title = r.get("title") or r.get("name") or ""
            url = r.get("url") or r.get("link") or ""
            content = r.get("content") or r.get("snippet") or ""
        if not url:
            continue
        display_link = None
        try:
            display_link = urlparse(url).netloc or url
        except Exception:
            pass
        results.append(
            GoogleSearchResult(
                title=title or url,
                link=url,
                snippet=str(content)[:500] if content else "",
                display_link=display_link,
            )
        )

    # 审计：记录每次调用
    append_tavily_audit(
        query=query,
        credits_used=credits,
        search_depth=search_depth,
        num_results=len(results),
        response_time=response_time,
    )

    resp_time_val = raw.get("response_time") if isinstance(raw, dict) else getattr(raw, "response_time", None)
    resp_time_val = resp_time_val or response_time
    return GoogleSearchResponse(
        results=results,
        total_results=None,
        search_time=float(resp_time_val) if resp_time_val is not None else response_time,
        query=query,
    )
