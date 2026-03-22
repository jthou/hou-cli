# 时间：2026-03-21；理由：事实包构建可单测；方法：无 DB、无 LLM
from __future__ import annotations

from backend.services.home_briefing.fact_pack import build_fact_pack_from_tasks


def test_build_fact_pack_empty():
    pack, ver = build_fact_pack_from_tasks([], window_hours=24, max_facts=10)
    assert pack["items"] == []
    assert len(ver) == 24


def test_build_fact_pack_web_search():
    tasks = [
        {
            "task_id": "t-1",
            "task_type": "web_search",
            "created_at": "2099-01-01T12:00:00+00:00",
            "result": {
                "status": "success",
                "summary": "ok",
                "query": "news",
                "result": {
                    "results": [
                        {"title": "A", "snippet": "sa", "link": "https://a"},
                        {"title": "B", "snippet": "sb", "link": "https://b"},
                    ],
                    "query": "news",
                },
            },
        }
    ]
    pack, _ver = build_fact_pack_from_tasks(tasks, window_hours=24 * 365, max_facts=10)
    assert len(pack["items"]) == 2
    assert pack["items"][0]["id"] == "F1"
    assert pack["items"][0]["task_type"] == "web_search"


def test_build_fact_pack_skips_non_success():
    tasks = [
        {
            "task_id": "t-1",
            "task_type": "web_search",
            "created_at": "2099-01-01T12:00:00+00:00",
            "result": {"status": "error"},
        }
    ]
    pack, _ = build_fact_pack_from_tasks(tasks, window_hours=168, max_facts=10)
    assert pack["items"] == []
