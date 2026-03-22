# 时间：2026-03-21；理由：简报正文由 LLM 根据事实包生成；方法：固定章节提示词 + LLMService.chat
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# 时间：2026-03-22；理由：产品要求「链接与要点在正文、少依赖文末列表」；方法：PROMPT_VERSION v2 + 正文内 Markdown 链接与高密度叙述规则
PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """你是「首页简报」编辑，只根据给定「事实包」JSON 写中文分析报告。
硬性规则：
1. 不得编造事实包中不存在的数据、链接或事件；未提供的信息在「本期局限」说明。
2. 引用标注：引用事实时使用 [F1]、[F2] 等，与事实包 items[].id 一致。
3. **来源链接写在正文内（必读）**：若某条事实的 `url` 字段非空字符串，你在首次引用该 [Fx] 的同一小节内，必须写出至少一个 Markdown 超链接，格式为 `[简短来源名或标题](完整url)`（url 须与事实包中该条完全一致），与 [Fx] 同句或紧邻；读者应**仅阅读正文**即可获知要点与可点击原文入口。**禁止**只在文末或附录才首次给出链接、而正文无可点击出处。`url` 为空的事实（如天气类）可只保留 [Fx]，不写链接。
4. **信息密度（必读）**：充分利用每条事实的 `title`、`summary` 中的具体信息（数据、机构、事件要点、引述措辞），写入「执行摘要」「分主题分析」「交叉与矛盾」；能用正文说清楚的就不要让读者依赖「再去翻原文」；避免用一两句空泛概括代替事实包已给出的细节。
5. 输出必须是 Markdown；包含以下二级标题（按顺序）：
## 执行摘要
## 分主题分析
## 交叉与矛盾
## 本期局限
6. 语气客观、有信息量；执行摘要可至约 28 行以内（素材多时可分段），以承载规则 4 的细节。"""


def _build_user_prompt(fact_pack: Dict[str, Any]) -> str:
    body = {
        "window": {
            "start": fact_pack.get("window_start"),
            "end": fact_pack.get("window_end"),
            "hours": fact_pack.get("window_hours"),
        },
        "truncated": fact_pack.get("truncated"),
        "items": fact_pack.get("items") or [],
    }
    return (
        "请根据以下事实包撰写简报（Markdown）。\n"
        "再次强调：含 url 的条目须在正文相应位置写出 `[锚文](url)` 并与 [Fx] 一起出现；把 summary 里的关键信息写进正文。\n\n"
        + json.dumps(body, ensure_ascii=False, indent=2)
    )


def _fact_refs(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(
            {
                "id": it.get("id"),
                "task_id": it.get("task_id"),
                "task_type": it.get("task_type"),
                "title": it.get("title"),
                "url": it.get("url") or "",
            }
        )
    return out


async def generate_briefing_markdown(
    fact_pack: Dict[str, Any],
    fact_pack_version: str,
    *,
    model: Optional[str] = None,
) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns:
        (markdown, meta_dict, fact_refs)
    """
    items = fact_pack.get("items") or []
    fact_refs = _fact_refs(items)

    if not items:
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "title": "简报 · 暂无数据",
            "window_start": fact_pack.get("window_start"),
            "window_end": fact_pack.get("window_end"),
            "generated_at": now,
            "fact_pack_version": fact_pack_version,
            "agent": "home_briefing_report",
            "model": model or "",
            "prompt_version": PROMPT_VERSION,
            "empty": True,
        }
        md = (
            "## 执行摘要\n\n"
            "当前时间窗口内没有可用的天气或网页搜索类任务结果，无法生成研判。\n\n"
            "## 本期局限\n\n"
            "- 请先完成至少一次 **天气查询** 或 **网页搜索**（或搜索对比）任务后再生成简报。\n"
        )
        return md, meta, fact_refs

    from backend.services.llm.llm_service import LLMService

    llm = LLMService(temperature=0.45, model=model) if model else LLMService(temperature=0.45)
    user_prompt = _build_user_prompt(fact_pack)
    audit_meta = {"kind": "home_briefing_report", "fact_pack_version": fact_pack_version}
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

    now = datetime.now(timezone.utc).isoformat()
    title_ts = now[:16].replace("T", " ")
    meta = {
        "title": f"简报 · {title_ts}",
        "window_start": fact_pack.get("window_start"),
        "window_end": fact_pack.get("window_end"),
        "generated_at": now,
        "fact_pack_version": fact_pack_version,
        "agent": "home_briefing_report",
        "model": getattr(llm, "model", "") or "",
        "prompt_version": PROMPT_VERSION,
        "used_count": len(items),
        "empty": False,
    }
    return text, meta, fact_refs
