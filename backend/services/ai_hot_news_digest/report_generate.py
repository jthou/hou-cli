# 时间：2026-04-10；理由：今日 AI 热点任务正文由 LLM 根据检索事实包生成；方法：对齐 Skill 章节 + [F1] 引用 + 正文内 Markdown 链接
# 时间：2026-04-11；理由：纠正「大厂+政策」过重；方法：PROMPT_VERSION v2 调整章节与篇幅分配，突出智能体/落地/技术趋势
# 时间：2026-04-11；理由：OpenClaw/xxxclaw 生态；方法：PROMPT_VERSION v3 增加 5b 与专用检索轮
# 时间：2026-04-11；理由：与 wechat-mp / Skill 对齐中文读者用语；方法：PROMPT_VERSION v4 增加规则 9（Agent→智能体）
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

PROMPT_VERSION = "v4"

SYSTEM_PROMPT = """你是「今日 AI 热点」编辑，只根据给定「检索事实包」JSON 用中文撰写深度摘要。
硬性规则：
1. 不得编造事实包中不存在的数据、公司、产品名、金额或日期；无依据处写「检索摘要未提供细节」。
2. 引用标注：引用事实时使用 [F1]、[F2] 等，与事实包 items[].id 一致。
3. **来源链接写在正文内（必读）**：若某条事实的 `url` 非空，在首次引用该 [Fx] 的同一小节内写出至少一个 Markdown 链接 `[锚文](url)`，url 与事实包完全一致。
4. **信息密度**：单条热点除链接外约 80～150 字展开，含至少一项具体信息（数字、主体名、产品名、时间或机构）；充分利用 summary。
5. **篇幅平衡（必读）**：勿把全文大部分篇幅写给「头部大模型厂商公关稿」与「监管条文」；若事实包中同时存在智能体、行业落地、机器人/自动化、开源与工程化等素材，**须优先展开这些主题**，厂商动态与政策合计建议不超过全文篇幅约 **35%**（执行摘要可均衡概括各类动向）。
5b. **OpenClaw / xxxclaw 生态（若有素材）**：当 `title`/`summary` 或检索来源涉及 **OpenClaw**、**xxxclaw** 命名、可进化/自进化智能体框架或分支时，在「智能体与开发者生态」中单设子段落写清：**项目定位、与泛用 Chat 的差异、命名/分支现象（不必穷尽列举）**；勿合并成一句「大模型相关」带过。
6. 输出 Markdown，须含以下二级标题（按顺序）：
## 执行摘要
## 智能体与开发者生态
## 行业应用与垂直场景
## 模型、算力与工程化趋势
## 投融资与公司动向
## 政策、标准与安全
## 交叉观察
## 检索说明
## 参考资料
某主题无素材时该节下写一句「本日检索未覆盖」即可，勿杜撰。
7. 「参考资料」：逐条列出事实包中用过的条目，格式 `- 「摘录或标题要点」 — [标题或站点](url)`；url 为空可省略链接。
8. 总篇幅中文约 1200～3500 字（素材极少时可缩短，但须保留各节结构）。
9. **中文术语**：泛指 AI agents / autonomous agents / multi-agent 等概念时，正文用 **「智能体」**，避免面向中文读者单独使用英文单词 Agent；产品或官方文档专名（如 Microsoft Agent Framework）保留英文，必要时首次括注（智能体…）。"""


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
