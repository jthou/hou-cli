"""开发审计 API：读取审计报告并返回给前端"""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

# 审计报告路径（相对于项目根）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = PROJECT_ROOT / "docs" / "audit"
REPORT_FILE = AUDIT_DIR / "AUDIT_REPORT.json"


@router.get("/audit/report")
async def get_audit_report():
    """返回完整审计报告（代码统计、开发历史、API 审计）"""
    if not REPORT_FILE.exists():
        raise HTTPException(status_code=404, detail="审计报告不存在，请先执行 make audit")
    try:
        data = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        return {"ok": True, "data": data}
    except Exception as e:
        logger.exception("读取审计报告失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/summary")
async def get_audit_summary():
    """返回审计摘要（用于仪表盘）"""
    if not REPORT_FILE.exists():
        return {"ok": True, "data": None, "message": "审计报告不存在"}
    try:
        raw = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        code = raw.get("code_stats") or {}
        dev = raw.get("dev_history") or {}
        api = raw.get("api_audit") or {}
        summary = {
            "generated_at": raw.get("generated_at"),
            "total_lines": code.get("total_lines"),
            "total_files": code.get("total_files"),
            "total_commits": dev.get("total_commits"),
            "backend_routes": api.get("backend_path_count"),
            "frontend_fetches": api.get("frontend_fetch_count"),
        }
        return {"ok": True, "data": summary}
    except Exception as e:
        logger.exception("读取审计摘要失败")
        raise HTTPException(status_code=500, detail=str(e))
