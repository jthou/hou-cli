"""
article_writing_message_contract：与前端 referenceUtils 对齐的契约测试（离线）。
时间：2026-03-21；理由：CLI/UI/编排单一来源；方法：pytest
"""
import pytest

from backend.core.agent.article_writing_message_contract import (
    REFERENCE_INTRO,
    USER_QUESTION_MARKER,
    build_article_draft_scope_prefix,
    build_article_sectioning_hint_injection,
    build_article_word_count_constraint_injection,
    build_message_for_model,
    format_reference_context,
    is_no_reference_placeholder,
    normalize_reference_blocks,
    task_triggers_doc_coauthoring,
)


def test_no_reference_is_plain_user_text():
    assert build_message_for_model([], "  hi  ") == "hi"
    assert build_message_for_model([{"content": "  "}], "y") == "y"


def test_format_reference_context_one_block():
    ctx = format_reference_context([{"title": "T", "content": "C"}])
    assert ctx.startswith(REFERENCE_INTRO)
    assert "【参考1：T】\nC" in ctx
    assert ctx.endswith("\n\n---\n\n")


def test_build_message_concat_equals_ui_pattern():
    blocks = [{"title": "", "content": "body"}]
    ref = format_reference_context(blocks)
    full = build_message_for_model(blocks, "Q")
    assert full == f"{ref}{USER_QUESTION_MARKER}\nQ"


def test_task_triggers_doc_coauthoring():
    assert task_triggers_doc_coauthoring("随便") is False
    assert task_triggers_doc_coauthoring("写PRD大纲") is True
    assert task_triggers_doc_coauthoring("", session_workflow="doc_coauthoring") is True


def test_is_no_reference_placeholder():
    assert is_no_reference_placeholder("（无）") is True
    assert is_no_reference_placeholder("(无)") is True
    assert is_no_reference_placeholder("  ") is True
    assert is_no_reference_placeholder("有内容") is False


def test_normalize_reference_blocks():
    assert normalize_reference_blocks([{"content": "a"}, {"content": ""}]) == [
        {"title": "", "content": "a"}
    ]


def test_word_count_injection_2000_zuoyou():
    s = "新写全文, 2000字左右"
    inj = build_article_word_count_constraint_injection(s)
    assert "2000" in inj and "1700" in inj and "2300" in inj
    assert "系统检出" in inj


def test_word_count_injection_none_when_no_pattern():
    assert build_article_word_count_constraint_injection("随便写写") == ""


def test_sectioning_hint_for_xin_xie_quan_wen():
    s = "新写全文, 2000字左右"
    inj = build_article_sectioning_hint_injection(s)
    assert "长文版式" in inj and "引言" in inj and "01" in inj


def test_sectioning_hint_suppressed_when_no_subtitles():
    s = "新写全文, 2000字左右，不要小标题"
    assert build_article_sectioning_hint_injection(s) == ""


def test_sectioning_hint_no_conclusion_when_user_forbids():
    s = "写一篇长文章，不要结论"
    inj = build_article_sectioning_hint_injection(s)
    assert "不要添加 `## 结论`" in inj


def test_draft_scope_prefix_empty_when_no_article():
    assert build_article_draft_scope_prefix("") == ""
    assert build_article_draft_scope_prefix("   ") == ""
    assert build_article_draft_scope_prefix(None) == ""


def test_draft_scope_prefix_contains_marker_and_rules():
    p = build_article_draft_scope_prefix("## 标题\n正文")
    assert "【改稿范围（须遵守）】" in p
    assert "【当前文章（右侧草稿）】" in p
    assert "## 标题\n正文" in p
    assert "局部" in p or "patch" in p
    assert "\n---\n\n" in p
