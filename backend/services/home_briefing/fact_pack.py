# 时间：2026-03-21；理由：P0 专用简报 Agent 输入；方法：从已完成任务 result 抽取结构化事实，供 LLM 写报告
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

SOURCE_TASK_TYPES = ("weather_query", "web_search", "web_search_compare")

DEFAULT_WINDOW_HOURS = 168
DEFAULT_MAX_FACTS = 40
# 时间：2026-03-22；理由：简报正文要高信息密度；方法：提高单条摘要进入事实包的上限，供 LLM 写入正文
MAX_SNIPPET_LEN = 800


def _parse_task_created_at(created_at: Optional[str]) -> Optional[datetime]:
    if not created_at or not isinstance(created_at, str):
        return None
    s = created_at.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(created_at.strip()[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _window_start_utc(hours: int) -> datetime:
    h = max(1, min(hours, 24 * 30))
    return datetime.now(timezone.utc) - timedelta(hours=h)


def _severity_weather(warning_list: List[Any]) -> str:
    if warning_list:
        return "alert"
    return "info"


def _facts_from_weather(task_id: str, created_at: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    loc = (data.get("location") or "").strip()
    inner = data.get("result") if isinstance(data.get("result"), dict) else data
    if not isinstance(inner, dict):
        inner = data
    warnings = inner.get("warning") or []
    if not isinstance(warnings, list):
        warnings = []
    parts = []
    cur = inner.get("current_weather") or {}
    if isinstance(cur, dict) and (cur.get("text") or cur.get("temp") is not None):
        parts.append(f"实时：{cur.get('text', '')} {cur.get('temp', '')}°C".strip())
    daily = inner.get("daily") or []
    if isinstance(daily, list) and daily:
        parts.append(f"预报 {len(daily)} 天")
    if warnings:
        titles = [w.get("title") or w.get("type") or str(w) for w in warnings[:5] if isinstance(w, dict)]
        parts.append("预警：" + "；".join(titles) if titles else f"预警 {len(warnings)} 条")
    air = inner.get("air_quality") or {}
    if isinstance(air, dict) and (air.get("aqi") or air.get("category")):
        parts.append(f"空气质量 AQI {air.get('aqi', '')} {air.get('category', '')}".strip())
    summary = " ".join(parts).strip() or (data.get("summary") or "天气数据")
    title = f"天气 · {loc}" if loc else "天气查询"
    return [
        {
            "id": "",
            "task_id": task_id,
            "task_type": "weather_query",
            "captured_at": created_at,
            "title": title[:200],
            "summary": summary[:MAX_SNIPPET_LEN],
            "url": "",
            "severity": _severity_weather(warnings),
        }
    ]


def _facts_from_web_search(task_id: str, created_at: str, data: Dict[str, Any], per_result_cap: int) -> List[Dict[str, Any]]:
    inner = data.get("result") if isinstance(data.get("result"), dict) else data
    if not isinstance(inner, dict):
        return []
    results = inner.get("results") or []
    if not isinstance(results, list):
        return []
    q = (inner.get("query") or data.get("query") or "").strip()
    out: List[Dict[str, Any]] = []
    for r in results[:per_result_cap]:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "无标题")[:200]
        snippet = (r.get("snippet") or "")[:MAX_SNIPPET_LEN]
        link = (r.get("link") or "")[:2000]
        out.append(
            {
                "id": "",
                "task_id": task_id,
                "task_type": "web_search",
                "captured_at": created_at,
                "title": f"搜索「{q[:40]}」· {title}" if q else title,
                "summary": snippet,
                "url": link,
                "severity": "info",
            }
        )
    return out


def _facts_from_web_search_compare(task_id: str, created_at: str, data: Dict[str, Any], per_side: int) -> List[Dict[str, Any]]:
    inner = data.get("result") if isinstance(data.get("result"), dict) else data
    if not isinstance(inner, dict):
        return []
    q = (data.get("query") or "").strip()
    out: List[Dict[str, Any]] = []
    for side, key in (("Tavily", "tavily"), ("DuckDuckGo", "duckduckgo")):
        block = inner.get(key) or {}
        if not isinstance(block, dict):
            continue
        results = block.get("results") or []
        if not isinstance(results, list):
            continue
        for r in results[:per_side]:
            if not isinstance(r, dict):
                continue
            title = (r.get("title") or "无标题")[:200]
            snippet = (r.get("snippet") or "")[:MAX_SNIPPET_LEN]
            link = (r.get("link") or "")[:2000]
            out.append(
                {
                    "id": "",
                    "task_id": task_id,
                    "task_type": "web_search_compare",
                    "captured_at": created_at,
                    "title": f"{side} ·「{q[:30]}」· {title}" if q else f"{side} · {title}",
                    "summary": snippet,
                    "url": link,
                    "severity": "info",
                }
            )
    return out


def build_fact_pack_from_tasks(
    tasks: List[Dict[str, Any]],
    *,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    max_facts: int = DEFAULT_MAX_FACTS,
) -> Tuple[Dict[str, Any], str]:
    window_start = _window_start_utc(window_hours)
    window_end = datetime.now(timezone.utc)
    items: List[Dict[str, Any]] = []
    truncated = False

    for t in tasks:
        if not isinstance(t, dict):
            continue
        tt = (t.get("task_type") or "").strip()
        if tt not in SOURCE_TASK_TYPES:
            continue
        tid = t.get("task_id") or ""
        cat = t.get("created_at") or ""
        dt = _parse_task_created_at(cat)
        if dt is not None and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt is not None and dt < window_start:
            continue
        res = t.get("result")
        if not isinstance(res, dict) or res.get("status") != "success":
            continue

        if tt == "weather_query":
            chunk = _facts_from_weather(tid, cat, res)
        elif tt == "web_search":
            chunk = _facts_from_web_search(tid, cat, res, 8)
        elif tt == "web_search_compare":
            chunk = _facts_from_web_search_compare(tid, cat, res, 6)
        else:
            chunk = []

        for c in chunk:
            if len(items) >= max_facts:
                truncated = True
                break
            items.append(c)
        if len(items) >= max_facts:
            truncated = True
            break

    for i, it in enumerate(items, start=1):
        it["id"] = f"F{i}"

    pack = {
        "schema_version": "1",
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "window_hours": window_hours,
        "items": items,
        "truncated": truncated,
        "source_task_types": list(SOURCE_TASK_TYPES),
    }
    canonical = json.dumps(
        {"items": [{k: v for k, v in it.items() if k != "id"} for it in items]},
        ensure_ascii=False,
        sort_keys=True,
    )
    version = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return pack, version
