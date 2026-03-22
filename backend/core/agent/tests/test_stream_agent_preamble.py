"""stream_agent_preamble：身份与编排摘要前缀"""
import pytest

from backend.core.agent.stream_agent_preamble import (
    iter_stream_preamble_text,
    resolve_stream_agent_preamble_mode,
)


def test_resolve_default_off(monkeypatch):
    monkeypatch.delenv("STREAM_AGENT_PREAMBLE", raising=False)
    monkeypatch.delenv("STREAM_AGENT_PREAMBLE_MODE", raising=False)
    assert resolve_stream_agent_preamble_mode({}) == "off"
    assert resolve_stream_agent_preamble_mode({"stream_agent_preamble": "full"}) == "full"


def test_iter_off_empty():
    assert list(iter_stream_preamble_text("off", branch="llm_plain", ctx_type="article_writing", is_work_assistant=False, is_general_chat=False, matched_skill_name=None, selected_model="m", skill_prematch_skipped=False, tools_count=0)) == []


def test_iter_identity_writing():
    parts = "".join(
        iter_stream_preamble_text(
            "identity",
            branch="llm_plain",
            ctx_type="article_writing",
            is_work_assistant=False,
            is_general_chat=False,
            matched_skill_name=None,
            selected_model="qwen3-max",
            skill_prematch_skipped=False,
            tools_count=0,
        )
    )
    assert "【我是写作助手Agent】" in parts
    assert "编排协调" not in parts


def test_iter_full_includes_orchestrator_line():
    parts = "".join(
        iter_stream_preamble_text(
            "full",
            branch="llm_plain",
            ctx_type="article_writing",
            is_work_assistant=False,
            is_general_chat=False,
            matched_skill_name=None,
            selected_model="qwen3-max",
            skill_prematch_skipped=True,
            tools_count=0,
        )
    )
    assert "【我是写作助手Agent】" in parts
    assert "【我是编排协调Agent】" in parts
    assert "技能预匹配=按配置跳过" in parts


def test_skill_branch():
    parts = "".join(
        iter_stream_preamble_text(
            "full",
            branch="skill",
            ctx_type="general_chat",
            is_work_assistant=False,
            is_general_chat=True,
            matched_skill_name="video_downloader",
            selected_model="m",
            skill_prematch_skipped=False,
            tools_count=0,
        )
    )
    assert "技能执行Agent · video_downloader" in parts
