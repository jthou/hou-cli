"""completed_tasks_prompt：格式化、相关性排序与可选注入行为单测。"""
from unittest.mock import patch

from backend.core.agent.completed_tasks_prompt import (
    build_completed_tasks_reference_block,
    format_completed_tasks_lines,
    rank_completed_tasks_for_query,
    score_completed_task_relevance,
)


def test_format_completed_tasks_lines_truncates_long_summary():
    tasks = [
        {
            "task_id": "tid-1",
            "task_name": "n",
            "task_type": "web_search",
            "completed_at": "2026-01-01T00:00:00Z",
            "result_summary": "x" * 300,
            "message": "",
        }
    ]
    out = format_completed_tasks_lines(tasks, summary_max=50)
    assert "tid-1" in out
    assert "…" in out
    assert len(out) < 400


def test_build_completed_tasks_reference_block_off_env():
    with patch.dict("os.environ", {"GENERAL_CHAT_INJECT_COMPLETED_TASKS": "false"}):
        assert build_completed_tasks_reference_block() == ""


def _sample_tasks(_lim: int):
    return [
        {
            "task_id": "abc",
            "task_name": "搜一下",
            "task_type": "web_search",
            "completed_at": "2026-01-02T00:00:00Z",
            "result_summary": "找到 3 条",
            "message": "",
        }
    ]


def test_build_completed_tasks_reference_block_success():
    with patch.dict("os.environ", {"GENERAL_CHAT_INJECT_COMPLETED_TASKS": "true"}):
        block = build_completed_tasks_reference_block(_fetch_completed=_sample_tasks)
    assert "【已完成任务" in block
    assert "task_id=abc" in block
    assert "web_search" in block


def test_score_wiki_prefers_matching_fields():
    t_match = {
        "task_id": "a",
        "task_name": "wiki 页面",
        "task_type": "url_to_wiki",
        "result_summary": "",
        "message": "",
    }
    t_other = {
        "task_id": "b",
        "task_name": "下载视频",
        "task_type": "video_download",
        "result_summary": "",
        "message": "",
    }
    assert score_completed_task_relevance(t_match, "wiki 同步") > score_completed_task_relevance(
        t_other, "wiki 同步"
    )


def test_rank_puts_higher_score_first():
    tasks = [
        {
            "task_id": "1",
            "task_name": "杂项",
            "task_type": "noop",
            "completed_at": "a",
            "result_summary": "",
            "message": "",
        },
        {
            "task_id": "2",
            "task_name": "wiki 同步",
            "task_type": "url_to_wiki",
            "completed_at": "b",
            "result_summary": "ok",
            "message": "",
        },
    ]
    out, fallback = rank_completed_tasks_for_query(tasks, "wiki 怎么做", top_k=2)
    assert not fallback
    assert out[0]["task_id"] == "2"


def test_rank_fallback_when_zero_score():
    tasks = [
        {
            "task_id": "1",
            "task_name": "aaa",
            "task_type": "noop",
            "completed_at": "a",
            "result_summary": "",
            "message": "",
        },
        {
            "task_id": "2",
            "task_name": "bbb",
            "task_type": "noop",
            "completed_at": "b",
            "result_summary": "",
            "message": "",
        },
    ]
    out, fallback = rank_completed_tasks_for_query(tasks, "zzzzunique_nohit", top_k=1)
    assert fallback
    assert out[0]["task_id"] == "1"


def test_build_uses_relevance_and_marker_query():
    def _fetch(_lim: int):
        return [
            {
                "task_id": "1",
                "task_name": "无关",
                "task_type": "noop",
                "completed_at": "a",
                "result_summary": "",
                "message": "",
            },
            {
                "task_id": "2",
                "task_name": "wiki 任务",
                "task_type": "url_to_wiki",
                "completed_at": "b",
                "result_summary": "done",
                "message": "",
            },
        ]

    env = {
        "GENERAL_CHAT_INJECT_COMPLETED_TASKS": "true",
        "GENERAL_CHAT_COMPLETED_TASKS_RELEVANCE": "true",
        "GENERAL_CHAT_COMPLETED_TASKS_POOL": "10",
        "GENERAL_CHAT_COMPLETED_TASKS_LIMIT": "2",
    }
    big_ref = "…" * 100
    user_msg = f"参考：{big_ref}\n【用户本次提问】\nwiki 相关"
    with patch.dict("os.environ", env, clear=False):
        block = build_completed_tasks_reference_block(
            current_user_query=user_msg,
            _fetch_completed=_fetch,
        )
    assert "关键词打分" in block
    p2 = block.find("task_id=2")
    p1 = block.find("task_id=1")
    assert p2 != -1 and p1 != -1 and p2 < p1
