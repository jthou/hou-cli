"""LLM 对话审计只读 API：列表日期、分页查询单条记录"""
from typing import Optional

from fastapi import APIRouter

router = APIRouter()


@router.get("/settings/llm-audit/dates")
async def list_llm_audit_dates():
    """返回已有审计文件的日期列表，格式 YYYY-MM-DD，降序。"""
    try:
        from backend.services.llm.llm_audit import list_audit_dates
        dates = list_audit_dates()
        return {"success": True, "dates": dates}
    except Exception as e:
        return {"success": False, "error": str(e), "dates": []}


@router.get("/settings/llm-audit/list")
async def list_llm_audit_records(
    date: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
):
    """
    分页读取审计记录，按时间倒序（最新在前）。
    - 单日：传 date=YYYY-MM-DD
    - 时间区间：传 from_date=YYYY-MM-DD&to_date=YYYY-MM-DD（可含“全部”即所有已有日期）
    """
    offset = max(0, offset)
    limit = min(max(1, limit), 100)
    try:
        from backend.services.llm.llm_audit import read_audit_records, read_audit_records_range
        if from_date and to_date:
            records, total = read_audit_records_range(
                from_date, to_date, offset=offset, limit=limit
            )
            return {
                "success": True,
                "mode": "range",
                "from_date": from_date,
                "to_date": to_date,
                "records": records,
                "total": total,
                "offset": offset,
                "limit": limit,
            }
        if date:
            records, total = read_audit_records(date, offset=offset, limit=limit)
            return {
                "success": True,
                "mode": "date",
                "date": date,
                "records": records,
                "total": total,
                "offset": offset,
                "limit": limit,
            }
        return {
            "success": False,
            "error": "请提供 date 或 from_date+to_date",
            "records": [],
            "total": 0,
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "records": [],
            "total": 0,
            "offset": offset,
            "limit": limit,
        }
