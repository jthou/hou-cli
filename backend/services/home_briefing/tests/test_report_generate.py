# 时间：2026-03-22；理由：简报提示词迭代需可回归；方法：校验关键规则字符串与 PROMPT_VERSION
from __future__ import annotations

from backend.services.home_briefing import report_generate


def test_prompt_version_v2():
    assert report_generate.PROMPT_VERSION == "v2"


def test_system_prompt_requires_inline_links_and_density():
    assert "Markdown 超链接" in report_generate.SYSTEM_PROMPT
    assert "信息密度" in report_generate.SYSTEM_PROMPT
    assert "正文内" in report_generate.SYSTEM_PROMPT


def test_user_prompt_includes_reminder():
    fp = {
        "window_start": "2099-01-01T00:00:00+00:00",
        "window_end": "2099-01-02T00:00:00+00:00",
        "window_hours": 24,
        "truncated": False,
        "items": [{"id": "F1", "title": "t", "summary": "s", "url": "https://example.com"}],
    }
    u = report_generate._build_user_prompt(fp)
    assert "再次强调" in u
    assert "[锚文](url)" in u
    assert "https://example.com" in u
