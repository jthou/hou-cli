# 时间：2026-04-10；理由：与 .agents/skills/ai-hot-news-summary 检索切面一致；方法：固定多查询模板 + 服务端当前日期注入
# 时间：2026-04-11；理由：减轻「大厂+政策」偏重；方法：增加智能体、垂直落地、具身/自动化、技术栈等检索角，扩至 8 轮
# 时间：2026-04-11；理由：覆盖 OpenClaw 系可进化智能体（社区俗称「龙虾」、多 xxxclaw 命名变种）；方法：专用检索轮次
from __future__ import annotations

from datetime import datetime
from typing import List


def default_ai_hot_news_queries(now: datetime) -> List[str]:
    """
    返回 9 条搜索语句（英/中混合），用于 Worker 内多次调用 unified_search.web_search。
    `now` 须为带时区的时间（建议 UTC，与任务队列一致）。
    """
    month_year_en = now.strftime("%B %Y")
    day_en = f"{now.strftime('%B')} {now.day}, {now.year}"
    zh_ym = f"{now.year}年{now.month}月"
    return [
        f"AI artificial intelligence news {day_en}",
        f"AI agent autonomous agent multi-agent workflow news {month_year_en}",
        f"OpenClaw evolvable AI agent xxxclaw naming autonomous agent news {month_year_en}",
        f"enterprise AI adoption vertical industry manufacturing healthcare finance news {month_year_en}",
        f"robotics embodied AI industrial automation smart factory news {month_year_en}",
        f"LLM inference RAG open source model tooling MCP context engineering news {month_year_en}",
        f"AI startup funding investment {month_year_en}",
        f"AI regulation policy government news {month_year_en}",
        f"人工智能 智能体 行业落地 垂直场景 {zh_ym}",
    ]
