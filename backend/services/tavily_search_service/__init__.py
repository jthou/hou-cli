"""Tavily 搜索服务（API 搜索，需 TAVILY_API_KEY，每月 1000 次免费额度）"""

from .tavily_search import search as tavily_search, TavilySearchError
from .tavily_usage_audit import (
    append_tavily_audit,
    get_tavily_usage_stats,
    get_tavily_audit_path,
)

__all__ = [
    "tavily_search",
    "TavilySearchError",
    "append_tavily_audit",
    "get_tavily_usage_stats",
    "get_tavily_audit_path",
]
