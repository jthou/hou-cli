"""Tavily API 调用审计只读 API：统计调用次数与 credits 消耗"""
from typing import Optional

from fastapi import APIRouter

router = APIRouter()


@router.get("/settings/tavily-audit/stats")
async def get_tavily_usage_stats(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """
    获取 Tavily API 调用统计（total_calls、total_credits、by_date）。
    可选 from_date、to_date（YYYY-MM-DD）过滤。
    """
    try:
        from backend.services.tavily_search_service.tavily_usage_audit import (
            get_tavily_usage_stats as _get_stats,
        )

        stats = _get_stats(from_date=from_date, to_date=to_date)
        return {"success": True, **stats}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_calls": 0,
            "total_credits": 0,
            "by_date": [],
        }


@router.get("/settings/tavily-audit/path")
async def get_tavily_audit_path():
    """返回 Tavily 审计数据库文件路径。"""
    try:
        from backend.services.tavily_search_service.tavily_usage_audit import (
            get_tavily_audit_path,
        )

        path = get_tavily_audit_path()
        return {"success": True, "path": path}
    except Exception as e:
        return {"success": False, "error": str(e), "path": None}
