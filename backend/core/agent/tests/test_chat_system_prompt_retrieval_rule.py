# 时间：2026-03-22；理由：财报/搜索类问题须提示先 google_search；方法：CHAT_SYSTEM_PROMPT 关键词单测
from __future__ import annotations

from backend.core.agent.system_prompt_templates import CHAT_SYSTEM_PROMPT


def test_chat_prompt_requires_search_before_financial_claims():
    assert "时效与事实检索" in CHAT_SYSTEM_PROMPT
    assert "google_search" in CHAT_SYSTEM_PROMPT
    assert "禁止" in CHAT_SYSTEM_PROMPT and "训练记忆" in CHAT_SYSTEM_PROMPT
