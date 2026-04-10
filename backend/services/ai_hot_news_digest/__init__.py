# 时间：2026-04-10；理由：UI「今日 AI 热点」任务独立模块；方法：多轮 web_search + LLM 成文
from backend.services.ai_hot_news_digest.report_generate import generate_ai_hot_news_markdown

__all__ = ["generate_ai_hot_news_markdown"]
