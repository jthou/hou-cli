# 时间：2026-04-10；理由：与 .cursor/skills/ai-hot-news-summary 检索切面一致；方法：固定多查询模板 + 服务端当前日期注入
from __future__ import annotations

from datetime import datetime
from typing import List


def default_ai_hot_news_queries(now: datetime) -> List[str]:
    """
    返回 5 条搜索语句（英/中混合），用于 Worker 内多次调用 unified_search.web_search。
    `now` 须为带时区的时间（建议 UTC，与任务队列一致）。
    """
    month_year_en = now.strftime("%B %Y")
    day_en = f"{now.strftime('%B')} {now.day}, {now.year}"
    zh_ym = f"{now.year}年{now.month}月"
    return [
        f"AI artificial intelligence news {day_en}",
        f"LLM OpenAI Google Anthropic announcement {month_year_en}",
        f"AI startup funding investment {month_year_en}",
        f"AI regulation EU NIST news {month_year_en}",
        f"人工智能 大模型 最新 {zh_ym}",
    ]
