"""
统一网页搜索入口：有 TAVILY_API_KEY 时用 Tavily（审计调用），否则用 DuckDuckGo。
"""
import os
from typing import Optional

from .models import GoogleSearchResponse


def web_search(
    query: str,
    num_results: int = 10,
    language: Optional[str] = None,
) -> GoogleSearchResponse:
    """
    统一网页搜索：TAVILY_API_KEY 存在时用 Tavily API（调用纳入审计），否则用 DuckDuckGo。

    Args:
        query: 搜索查询
        num_results: 返回结果数量（Tavily 最大 20，DuckDuckGo 可更大）
        language: 语言代码（可选）

    Returns:
        GoogleSearchResponse
    """
    if os.environ.get("TAVILY_API_KEY", "").strip():
        from backend.services.tavily_search_service import tavily_search
        from backend.services.tavily_search_service import TavilySearchError

        try:
            return tavily_search(
                query=query,
                num_results=min(num_results, 20),
                language=language,
                search_depth="basic",
            )
        except TavilySearchError as e:
            raise RuntimeError(f"Tavily 搜索失败: {e}") from e

    from .browser_search import search as browser_search, BrowserSearchError

    try:
        return browser_search(
            query=query,
            num_results=num_results,
            language=language,
        )
    except BrowserSearchError as e:
        raise RuntimeError(f"网页搜索失败: {e}") from e
