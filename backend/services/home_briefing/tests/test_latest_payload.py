# 时间：2026-03-21；理由：P1 降级横幅逻辑可回归；方法：build_latest_home_briefing_payload 单测
from __future__ import annotations

from backend.services.home_briefing.latest_payload import build_latest_home_briefing_payload


def _ok_task(tid: str, ts: str, gen_at: str):
    return {
        "task_id": tid,
        "task_type": "home_briefing_report",
        "status": "completed",
        "created_at": ts,
        "completed_at": ts,
        "result": {
            "status": "success",
            "summary": "ok",
            "result": {
                "briefing": {
                    "meta": {"generated_at": gen_at, "title": "T"},
                    "markdown": "# x",
                    "fact_refs": [],
                }
            },
        },
    }


def test_empty():
    out = build_latest_home_briefing_payload([])
    assert out["briefing"] is None
    assert out["last_attempt"] is None


def test_success_only():
    tasks = [_ok_task("s1", "2099-01-02T10:00:00", "2099-01-02T10:01:00")]
    out = build_latest_home_briefing_payload(tasks)
    assert out["briefing"] is not None
    assert out["show_degraded_banner"] is False
    assert out["pending_in_queue"] is False


def test_failed_after_success_shows_banner():
    ok = _ok_task("s1", "2099-01-01T10:00:00", "2099-01-01T10:05:00")
    failed = {
        "task_id": "f1",
        "task_type": "home_briefing_report",
        "status": "failed",
        "created_at": "2099-01-03T10:00:00",
        "completed_at": "2099-01-03T10:02:00",
        "error": "LLM timeout",
        "message": "",
        "result": None,
    }
    # recent DESC: failed first
    out = build_latest_home_briefing_payload([failed, ok])
    assert out["briefing"] is not None
    assert out["show_degraded_banner"] is True
    assert out["last_attempt"]["status"] == "failed"


def test_queued_shows_pending():
    q = {
        "task_id": "q1",
        "task_type": "home_briefing_report",
        "status": "queued",
        "created_at": "2099-01-04T10:00:00",
        "result": None,
    }
    ok = _ok_task("s1", "2099-01-01T10:00:00", "2099-01-01T10:05:00")
    out = build_latest_home_briefing_payload([q, ok])
    assert out["pending_in_queue"] is True
