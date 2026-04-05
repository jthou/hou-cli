# 时间：2026-03-22；理由：全文重写须落实修改意见与个人开篇；方法：ARTICLE_WRITING_SYSTEM_PROMPT_HEAD 关键词断言
from __future__ import annotations

from backend.core.agent.system_prompt_templates import ARTICLE_WRITING_SYSTEM_PROMPT_HEAD


def test_prompt_prioritizes_modification_opinion_over_generic_opening():
    assert "修改意见与全文重写" in ARTICLE_WRITING_SYSTEM_PROMPT_HEAD
    assert "基于以上修改意见重写" in ARTICLE_WRITING_SYSTEM_PROMPT_HEAD
    assert "个人经历" in ARTICLE_WRITING_SYSTEM_PROMPT_HEAD
    assert (
        "空话套话开篇" in ARTICLE_WRITING_SYSTEM_PROMPT_HEAD
        or "泛化引子" in ARTICLE_WRITING_SYSTEM_PROMPT_HEAD
        or "泛化鸡汤" in ARTICLE_WRITING_SYSTEM_PROMPT_HEAD
    )


def test_prompt_allows_personal_opening_when_user_asks():
    assert "例外（必读）" in ARTICLE_WRITING_SYSTEM_PROMPT_HEAD
    assert "不得以「避免口语化」为由省略" in ARTICLE_WRITING_SYSTEM_PROMPT_HEAD
