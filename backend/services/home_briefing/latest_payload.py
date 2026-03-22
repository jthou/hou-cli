# 时间：2026-03-21；理由：P1 失败仍展示上一期 + 顶栏提示；方法：纯函数便于单测
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def extract_briefing_from_task_result(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    res = task.get("result")
    if not isinstance(res, dict) or res.get("status") != "success":
        return None
    inner = res.get("result")
    if not isinstance(inner, dict):
        return None
    br = inner.get("briefing")
    return br if isinstance(br, dict) else None


def _is_newer(a: Optional[str], b: Optional[str]) -> bool:
    """字符串时间比较（ISO 或同格式）。"""
    if not a:
        return False
    if not b:
        return True
    return (a or "").strip() > (b or "").strip()


def build_latest_home_briefing_payload(
    recent_home_briefing_tasks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    recent_home_briefing_tasks: list_tasks(..., task_types=[home_briefing_report], status=None)
    已按 created_at DESC。
    """
    recent = [t for t in recent_home_briefing_tasks if isinstance(t, dict)]

    success_task: Optional[Dict[str, Any]] = None
    for t in recent:
        if (t.get("status") or "").strip() == "completed":
            br = extract_briefing_from_task_result(t)
            if br:
                success_task = t
                break

    latest = recent[0] if recent else None
    latest_status = (latest.get("status") or "").strip() if latest else ""

    briefing = extract_briefing_from_task_result(success_task) if success_task else None

    out: Dict[str, Any] = {
        "success": True,
        "briefing": briefing,
        "task_id": success_task.get("task_id") if success_task else None,
        "created_at": success_task.get("created_at") if success_task else None,
        "completed_at": success_task.get("completed_at") if success_task else None,
        "show_degraded_banner": False,
        "last_attempt": None,
        "pending_in_queue": False,
    }

    if not latest:
        return out

    out["last_attempt"] = {
        "task_id": latest.get("task_id"),
        "status": latest_status,
        "error": (latest.get("error") or "").strip() or None,
        "message": (latest.get("message") or "").strip() or None,
        "created_at": latest.get("created_at"),
        "completed_at": latest.get("completed_at"),
    }

    if latest_status in ("queued", "running"):
        out["pending_in_queue"] = True

    if latest_status == "failed":
        err = out["last_attempt"]["error"] or out["last_attempt"]["message"] or "简报生成失败"
        out["last_attempt"]["display_error"] = err
        if success_task:
            # 失败发生在「上一期成功」之后 → 展示上一期 + 顶栏
            succ_done = success_task.get("completed_at") or success_task.get("created_at")
            fail_t = latest.get("completed_at") or latest.get("created_at")
            if _is_newer(fail_t, succ_done):
                out["show_degraded_banner"] = True
        else:
            out["show_degraded_banner"] = False

    return out
