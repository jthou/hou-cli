"""字节预算与消息清洗测试"""
import pytest
from backend.core.context.budget import (
    replace_oversized_messages,
    cap_array_by_json_bytes,
    enforce_history_budget,
    OVERSIZED_PLACEHOLDER,
    DEFAULT_MAX_SINGLE_MESSAGE_BYTES,
)
from backend.core.context.sanitize import (
    strip_envelope,
    sanitize_message_for_llm,
    sanitize_messages_for_llm,
)


class TestBudget:
    def test_replace_oversized(self):
        small = [{"role": "user", "content": "hi"}]
        out, n = replace_oversized_messages(small, max_single_message_bytes=1000)
        assert n == 0
        assert out[0]["content"] == "hi"

    def test_replace_oversized_placeholder(self):
        big = [{"role": "user", "content": "x" * 2000}]
        out, n = replace_oversized_messages(big, max_single_message_bytes=500)
        assert n == 1
        assert out[0]["content"] == OVERSIZED_PLACEHOLDER

    def test_cap_array_by_bytes(self):
        items = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        capped, _ = cap_array_by_json_bytes(items, max_bytes=100)
        assert len(capped) < 10
        assert capped[-1]["content"] == "msg9"  # 保留尾部

    def test_enforce_history_budget(self):
        items = [{"role": "user", "content": "a" * 100} for _ in range(100)]
        out = enforce_history_budget(items, max_bytes=500, max_single_message_bytes=200)
        assert len(out) < 100


class TestSanitize:
    def test_strip_envelope_code_block(self):
        t = "```json\nhello\n```"
        assert strip_envelope(t) == "hello"

    def test_strip_envelope_plain(self):
        t = "plain text"
        assert strip_envelope(t) == "plain text"

    def test_sanitize_message_truncate(self):
        long_content = "x" * 100_000
        out = sanitize_message_for_llm({"role": "user", "content": long_content}, max_content_chars=1000)
        assert len(out["content"]) < 100_000
        assert "[truncated]" in out["content"]

    def test_sanitize_messages_batch(self):
        msgs = [
            {"role": "user", "content": "```\nhi\n```"},
            {"role": "assistant", "content": "ok"},
        ]
        out = sanitize_messages_for_llm(msgs)
        assert out[0]["content"] == "hi"
        assert out[1]["content"] == "ok"
