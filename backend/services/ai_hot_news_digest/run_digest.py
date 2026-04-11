# 时间：2026-04-04；理由：阅读页「今日 AI 热点」需 HTTP 直跑不入队，与 Worker 共用同一编排；方法：抽离为 async run_ai_hot_news_digest(metadata, on_progress=...)
"""今日 AI 热点：多轮 web_search + LLM 成文。供任务 Worker 与 POST /api/ai-hot-news/run 共用。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.services.ai_hot_news_digest.queries import default_ai_hot_news_queries
from backend.services.ai_hot_news_digest.report_generate import generate_ai_hot_news_markdown
from backend.services.google_search_service.unified_search import web_search


async def run_ai_hot_news_digest(
    metadata: Optional[Dict[str, Any]] = None,
    *,
    on_progress: Optional[Callable[[int, Optional[str]], None]] = None,
) -> Dict[str, Any]:
    """
    返回结构与 process_ai_hot_news_digest_task 一致：
    success 时 ``{"status": "success", "summary": ..., "result": {"digest": ...}}``。
    """
    metadata = metadata or {}

    def prog(pct: int, msg: Optional[str] = None) -> None:
        if on_progress:
            on_progress(pct, msg)

    num_results = metadata.get("num_results", 12)
    try:
        num_results = int(num_results)
    except (TypeError, ValueError):
        num_results = 12
    num_results = max(5, min(20, num_results))

    language = (metadata.get("language") or "").strip() or None
    model_override = (metadata.get("model") or "").strip() or None

    now = datetime.now(timezone.utc)
    queries = default_ai_hot_news_queries(now)
    retrieval_date = now.date().isoformat()

    query_logs: List[Dict[str, Any]] = []
    raw_rows: List[Dict[str, Any]] = []
    nq = len(queries)
    for i, q in enumerate(queries):
        pct = 5 + int(75 * i / max(nq, 1))
        prog(pct, f"检索 {i + 1}/{nq}…")
        try:
            resp = web_search(query=q, num_results=num_results, language=language)
            results = [
                {"title": r.title, "link": r.link, "snippet": r.snippet}
                for r in (resp.results or [])
            ]
            query_logs.append({"query": q, "count": len(results), "error": None})
            for r in results:
                raw_rows.append({**r, "_query": q})
        except Exception as e:
            query_logs.append({"query": q, "count": 0, "error": str(e)})

    seen: set = set()
    deduped: List[Dict[str, Any]] = []
    for r in raw_rows:
        link = (r.get("link") or "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        deduped.append(r)

    max_items = 55
    max_snippet = 800
    items: List[Dict[str, Any]] = []
    for idx, r in enumerate(deduped[:max_items], start=1):
        title = (r.get("title") or "无标题")[:200]
        snippet = (r.get("snippet") or "")[:max_snippet]
        link = (r.get("link") or "")[:2000]
        q_src = (r.get("_query") or "")[:120]
        items.append(
            {
                "id": f"F{idx}",
                "title": (f"搜索「{q_src[:40]}」· {title}" if q_src else title),
                "summary": snippet,
                "url": link,
            }
        )

    bundle = {
        "retrieval_date": retrieval_date,
        "timezone_note": "检索词日期按服务器 UTC 注入；与用户本地「今日」可能相差一天。",
        "queries_run": query_logs,
        "items": items,
    }

    prog(88, "正在生成深度摘要…")
    markdown, meta, source_refs = await generate_ai_hot_news_markdown(bundle, model=model_override)

    digest = {
        "schema_version": "1",
        "meta": meta,
        "markdown": markdown,
        "source_refs": source_refs,
        "search_log": query_logs,
    }
    summary = meta.get("title") or "今日 AI 热点已生成"

    prog(100, "今日 AI 热点生成完成")
    return {
        "status": "success",
        "summary": summary[:500],
        "result": {"digest": digest},
    }
