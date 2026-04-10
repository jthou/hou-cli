# 时间：2026-04-10；理由：回归空事实包与查询模板；方法：asyncio.run + monkeypatch，避免依赖 pytest-asyncio
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.services.ai_hot_news_digest.queries import default_ai_hot_news_queries
from backend.services.ai_hot_news_digest.report_generate import generate_ai_hot_news_markdown


def test_default_queries_five_and_zh_month():
    dt = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    qs = default_ai_hot_news_queries(dt)
    assert len(qs) == 5
    assert "April 10, 2026" in qs[0]
    assert "2026年4月" in qs[-1]


def test_generate_markdown_empty_items_skips_llm():
    md, meta, refs = asyncio.run(
        generate_ai_hot_news_markdown(
            {
                "retrieval_date": "2026-04-10",
                "queries_run": [{"query": "x", "count": 0, "error": "network"}],
                "items": [],
            }
        )
    )
    assert meta.get("empty") is True
    assert "执行摘要" in md
    assert refs == []

# 非空事实包路径需加载 llm_service（依赖 openai 等），在最小 CI/系统 Python 下不测；Worker 集成为准。
