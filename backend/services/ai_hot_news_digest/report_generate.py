# 时间：2026-04-10；理由：今日 AI 热点任务正文由 LLM 根据检索事实包生成；方法：对齐 Skill 章节 + [F1] 引用 + 正文内 Markdown 链接
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是「今日 AI 热点」编辑，只根据给定「检索事实包」JSON 用中文撰写深度摘要。
硬性规则：
1. 不得编造事实包中不存在的数据、公司、产品名、金额或日期；无依据处写「检索摘要未提供细节」。
2. 引用标注：引用事实时使用 [F1]、[F2] 等，与事实包 items[].id 一致。
3. **来源链接写在正文内（必读）**：若某条事实的 `url` 非空，在首次引用该 [Fx] 的同一小节内写出至少一个 Markdown 链接 `[锚文](url)`，url 与事实包完全一致。
4. **信息密度**：单条热点除链接外约 80～150 字展开，含至少一项具体信息（数字、主体名、产品名、时间或机构）；充分利用 summary。
5. 输出 Markdown，须含以下二级标题（按顺序）：
## 执行摘要
## 投融资与公司动向
## 模型与产品
## 政策、标准与安全
## 交叉观察
## 检索说明
## 参考资料
某主题无素材时该节下写一句「本日检索未覆盖」即可，勿杜撰。
6. 「参考资料」：逐条列出事实包中用过的条目，格式 `- 「摘录或标题要点」 — [标题或站点](url)`；url 为空可省略链接。
7. 总篇幅中文约 1200～3500 字（素材极少时可缩短，但须保留各节结构）。"""


def _build_user_prompt(bundle: Dict[str, Any]) -> str:
    slim = {
        "retrieval_date": bundle.get("retrieval_date"),
        "timezone_note": bundle.get("timezone_note"),
        "queries_run": bundle.get("queries_run") or [],
        "items": bundle.get("items") or [],
    }
    return (
        "请根据以下检索事实包撰写「今日 AI 热点深度摘要」（Markdown）。\n"
        "再次强调：含 url 的条目须在正文相应位置写出 Markdown 链接。\n\n"
        + json.dumps(slim, ensure_ascii=False, indent=2)
    )


def _refs_from_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(
            {
                "id": it.get("id"),
                "url": it.get("url") or "",
                "title": (it.get("title") or "")[:200],
            }
        )
    return out


async def generate_ai_hot_news_markdown(
    bundle: Dict[str, Any],
    *,
    model: Optional[str] = None,
) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns:
        (markdown, meta_dict, source_refs)
    """
    items = [x for x in (bundle.get("items") or []) if isinstance(x, dict)]
    fact_refs = _refs_from_items(items)
    now = datetime.now(timezone.utc).isoformat()

    if not items:
        meta = {
            "title": "今日 AI 热点 · 无检索结果",
            "retrieval_date": bundle.get("retrieval_date"),
            "generated_at": now,
            "agent": "ai_hot_news_digest",
            "model": "",
            "prompt_version": PROMPT_VERSION,
            "used_count": 0,
            "empty": True,
        }
        md = (
            "## 执行摘要\n\n"
            "本次任务的多轮网页检索均未返回可用结果（可能为网络、SSL、或未配置 TAVILY_API_KEY 且 DuckDuckGo 不可用）。请检查环境后重试。\n\n"
            "## 检索说明\n\n"
            "- 详见任务结果中的 `search_log`。\n"
        )
        return md, meta, fact_refs

    from backend.services.llm.llm_service import LLMService

    llm = LLMService(temperature=0.45, model=model) if model else LLMService(temperature=0.45)
    user_prompt = _build_user_prompt(bundle)
    audit_meta = {"kind": "ai_hot_news_digest", "prompt_version": PROMPT_VERSION}
    text = await llm.chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        audit_meta=audit_meta,
    )
    if not isinstance(text, str):
        text = str(text or "")
    text = text.strip()
    if not text:
        text = "## 执行摘要\n\n（模型未返回内容）\n"

    title_ts = now[:16].replace("T", " ")
    meta = {
        "title": f"今日 AI 热点 · {title_ts}",
        "retrieval_date": bundle.get("retrieval_date"),
        "generated_at": now,
        "agent": "ai_hot_news_digest",
        "model": getattr(llm, "model", "") or "",
        "prompt_version": PROMPT_VERSION,
        "used_count": len(items),
        "empty": False,
    }
    return text, meta, fact_refs
