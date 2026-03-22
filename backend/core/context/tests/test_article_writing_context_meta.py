# 时间：2026-03-13；理由：写作 __CTX_META__ 合同需回归；方法：纯函数断言 strategy 与 items
from __future__ import annotations

from backend.core.context.article_writing_context_meta import (
    build_article_writing_stream_ctx_meta,
    parse_first_ctx_meta_payload_from_stream_chunks,
    task_contains_reference_blocks,
    validate_article_writing_ctx_meta_response,
)


def test_build_article_writing_meta_minimal():
    m = build_article_writing_stream_ctx_meta(
        session_chat_turn_count=4,
        raw_task="仅一句",
        has_draft_injection=False,
        draft_char_count=0,
        draft_text_preview="",
        has_reference_blocks=False,
        has_profile_injection=False,
        profile_preview="",
        has_word_count_hint=False,
        has_section_hint=False,
    )
    assert m["type"] == "context_selection"
    assert m["strategy"] == "article_writing"
    assert m["total_in_session"] == 4
    assert len(m["items"]) == 1
    assert m["items"][0]["source"] == "user_turn"


def test_build_article_writing_meta_with_draft_and_profile():
    m = build_article_writing_stream_ctx_meta(
        session_chat_turn_count=2,
        raw_task="前缀【用户本次提问】\n改开篇",
        has_draft_injection=True,
        draft_char_count=100,
        draft_text_preview="第一行草稿",
        has_reference_blocks=False,
        has_profile_injection=True,
        profile_preview="第一人称",
        has_word_count_hint=True,
        has_section_hint=False,
    )
    assert m["used_count"] == 4
    sources = [it["source"] for it in m["items"]]
    assert sources == ["injected_draft", "injected_profile", "injected_constraints", "user_turn"]
    assert "改开篇" in m["query_preview"] or "改开篇" in (m["items"][-1].get("preview") or "")


def test_task_contains_reference_blocks():
    assert task_contains_reference_blocks("【参考1：标题】\n正文") is True
    assert task_contains_reference_blocks("以下是用户提供的参考资料\n") is True
    assert task_contains_reference_blocks("纯提问") is False


def test_build_article_writing_meta_with_reference():
    m = build_article_writing_stream_ctx_meta(
        session_chat_turn_count=0,
        raw_task="【参考1】x\n\n【用户本次提问】\n改",
        has_draft_injection=False,
        draft_char_count=0,
        draft_text_preview="",
        has_reference_blocks=True,
        has_profile_injection=False,
        profile_preview="",
        has_word_count_hint=False,
        has_section_hint=False,
    )
    assert [it["source"] for it in m["items"]] == ["injected_reference", "user_turn"]


def test_parse_and_validate_ctx_meta_helpers():
    chunks = [
        'x',
        '__CTX_META__:{"type":"context_selection","strategy":"article_writing","items":[{"source":"injected_reference"}]}',
    ]
    p = parse_first_ctx_meta_payload_from_stream_chunks(chunks)
    assert p is not None
    ok, msg = validate_article_writing_ctx_meta_response(p, expect_reference=True)
    assert ok and "通过" in msg
    bad, _ = validate_article_writing_ctx_meta_response(None, expect_reference=True)
    assert bad is False


def test_validate_ctx_meta_without_reference_ok_when_not_required():
    p = {
        "strategy": "article_writing",
        "items": [{"source": "user_turn"}],
    }
    ok, _ = validate_article_writing_ctx_meta_response(p, expect_reference=False)
    assert ok
    ok_strict, _ = validate_article_writing_ctx_meta_response(p, expect_reference=True)
    assert ok_strict is False
