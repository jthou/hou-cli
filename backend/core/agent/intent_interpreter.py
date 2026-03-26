# 时间：2026-03-22；理由：用户需要基于语义的意图验收，替代关键词脚本；方法：独立 LLM 调用 + 严格 JSON 合同，供测试与后续编排复用
"""
意图解读（写作修订场景）

- `explain_writing_instruction_intent`：仅从用户指令中抽取「用户到底要什么」（不读模型输出）。
- `judge_writing_output_vs_instruction`：判断模型输出是否在语义上满足用户指令（允许标点/语序微调，要求实质要点落地）。

二者均走 LLM，temperature 低；返回 dataclass，便于编排与单测解析函数。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 合同：仅允许这些顶层键，便于解析与回归
# ---------------------------------------------------------------------------

EXPLAIN_INTENT_SCHEMA_HINT = """只输出一个 JSON 对象，键为：
- intent_summary: string，一句话概括用户意图
- revision_scope: string，取值必须是以下之一：opening_only | conclusion_or_closing | section | full_article | unclear
- must_preserve_substance: string[]，仅用户明确要求写入正文且不得丢失的事实/数字/专名/原话（短句，勿空泛）；代码块内符号默认不算，除非用户明说写入正文
- stylistic_constraints: string[]，如 第一人称、术语中英混排、不要用「想象一下」套话 等；无则 []
- ambiguity_notes: string，若指令有歧义则说明，否则空字符串
"""

JUDGE_SCHEMA_HINT = """只输出一个 JSON 对象，键为：
- satisfied: boolean，模型输出是否在语义上满足用户指令
- confidence: string，取 high | medium | low
- rationale: string，2～5 句中文，说明判断依据
- unmet_points: string[]，若 satisfied 为 false，列出未落实的要点；若 true 可为空数组
"""


@dataclass
class WritingInstructionIntent:
    intent_summary: str
    revision_scope: str
    must_preserve_substance: List[str]
    stylistic_constraints: List[str]
    ambiguity_notes: str


@dataclass
class RevisionFulfillmentJudgment:
    satisfied: bool
    confidence: str
    rationale: str
    unmet_points: List[str] = field(default_factory=list)


def _strip_json_fence(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
    if m:
        return m.group(1).strip()
    return t


def parse_explain_intent_json(raw: str) -> WritingInstructionIntent:
    """从模型原文解析；失败时返回保守占位，避免测试崩溃。"""
    try:
        obj = json.loads(_strip_json_fence(raw))
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("explain intent JSON 解析失败: %s", e)
        return WritingInstructionIntent(
            intent_summary="（解析失败）",
            revision_scope="unclear",
            must_preserve_substance=[],
            stylistic_constraints=[],
            ambiguity_notes=raw[:200] if raw else "",
        )
    return WritingInstructionIntent(
        intent_summary=str(obj.get("intent_summary") or "").strip() or "（空）",
        revision_scope=str(obj.get("revision_scope") or "unclear").strip(),
        must_preserve_substance=_as_str_list(obj.get("must_preserve_substance")),
        stylistic_constraints=_as_str_list(obj.get("stylistic_constraints")),
        ambiguity_notes=str(obj.get("ambiguity_notes") or "").strip(),
    )


def parse_revision_judgment_json(raw: str) -> RevisionFulfillmentJudgment:
    try:
        obj = json.loads(_strip_json_fence(raw))
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("revision judgment JSON 解析失败: %s", e)
        return RevisionFulfillmentJudgment(
            satisfied=False,
            confidence="low",
            rationale=f"解析裁判 JSON 失败: {e}",
            unmet_points=["无法解析裁判输出"],
        )
    sat = obj.get("satisfied")
    if not isinstance(sat, bool):
        sat = str(sat).lower() in ("true", "1", "yes")
    return RevisionFulfillmentJudgment(
        satisfied=sat,
        confidence=str(obj.get("confidence") or "medium").strip(),
        rationale=str(obj.get("rationale") or "").strip() or "（无说明）",
        unmet_points=_as_str_list(obj.get("unmet_points")),
    )


def _as_str_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


EXPLAIN_SYSTEM = f"""你是「写作意图解读」助手，只做结构化抽取，不评价好坏、不生成正文。

【输入说明】
- 「【用户指令】」里可能混有：短句要求 + 用户粘贴的正文/对话/技术示例。只根据用户**自然语言直接提出的写作要求**抽取；勿把粘贴全文当作「用户口头列出的要点」逐条抄进 must_preserve_substance。
- Markdown 代码块（```…```）默认是示例、引用或技术片段，**不是**必须写入正文的要点清单。

{EXPLAIN_INTENT_SCHEMA_HINT}

【各字段细则】
- must_preserve_substance：仅当用户明确要求**写入正文、不得删改、必须保留**时收录；**不要**把代码里的函数名、命令、配置项当作要点，除非用户明说「这段要出现在正文里」「保留这段引用」等。
- 若用户要求用 patch / unified diff / ```patch``` 交稿：intent_summary 应体现「以补丁形式改稿」；**不要**把 patch 正文拆条塞进 must_preserve_substance。

【revision_scope 硬性规则】
- 仅当用户**明文**提到范围时才填具体值：如「开篇/引言/开头/第一段」→ opening_only；「结论/结语/收尾/最后一段」→ conclusion_or_closing；「全文/整篇/通篇」→ full_article；「某一节/第几段/下面这段/第二段/3.2 节」且能对应 → section。
- 若用户只写「修改意见」「优化」「润色」等**未指明改哪里**：**必须**填 **unclear**，**禁止**根据所附正文「看起来像引言还是结语」猜测 opening_only 或 conclusion_or_closing；也**禁止**仅因文中有代码块就推断 section。
- 在 ambiguity_notes 中简述范围不明时的建议（例如：请用户补充改全文还是改某段）。

【示例】（格式与边界说明；你回应真实【用户指令】时仍只输出**一条** JSON，勿照抄示例 JSON）
- 输入只有「改改」并附长文 → revision_scope=unclear，must_preserve_substance=[]，ambiguity_notes 建议用户指明范围。
- 输入「开头加个人经历，保留 2020 年那条线」→ opening_only，must_preserve_substance 含「2020 年叙事」类短句。
- 输入「文风正式一点」并附含 ```python 的大段代码 → stylistic_constraints 可含「正式、书面语」，revision_scope 多为 unclear（未说局部/全文），must_preserve_substance 不因代码块自动填充。

不要输出 Markdown 标题或解释性前言，只输出 JSON。"""

def format_intent_for_writing_prompt(intent: WritingInstructionIntent) -> str:
    """将意图解读结果格式化为写作主模型 user 侧可读的固定块。

    时间：2026-03-13；理由：编排侧需把「意图 agent」输出与「写作 agent」同轮次拼接；方法：统一【系统解读·用户写作意图】前缀 + 字段分行，供 ARTICLE_WRITING 主调参考。
    """
    lines = [
        "【系统解读·用户写作意图】（以下由意图解读子调用生成，请在正文写作中落实；若与上文参考草稿或用户原句冲突，以参考与用户原句为准）",
        f"- 意图摘要：{intent.intent_summary}",
        f"- 修订范围：{intent.revision_scope}",
    ]
    if intent.must_preserve_substance:
        lines.append("- 必须保留的要点：" + "；".join(intent.must_preserve_substance))
    if intent.stylistic_constraints:
        lines.append("- 风格/形式约束：" + "；".join(intent.stylistic_constraints))
    if intent.ambiguity_notes:
        lines.append(f"- 歧义说明：{intent.ambiguity_notes}")
    return "\n".join(lines)


JUDGE_SYSTEM = f"""你是「写作指令验收」助手：根据【用户指令】与【模型输出】判断是否落实用户意图。
规则：
- 以语义为准：允许标点、语序、书面化润色，但用户明确要求写入的经历、原话、数据必须在实质上出现。
- 若用户要求「个人经历开篇」而输出仍以「想象一下，未来…」等泛化套话开篇且未承接用户经历，判 satisfied=false。
- 若用户要求重写某段而输出完全未触及该段要点，判 false。
- 【用户指令】里未要求写入正文的代码块、技术示例、对话摘录，不得因其未出现在【模型输出】中而写入 unmet_points。
- 若用户意图是提交 patch/diff：重点看是否落实修改意图与补丁是否可对应草稿；不要求【模型输出】复述整段 patch 原文。
{JUDGE_SCHEMA_HINT}
不要输出 Markdown，只输出 JSON。"""


async def explain_writing_instruction_intent(
    user_instruction: str,
    *,
    model: Optional[str] = None,
) -> WritingInstructionIntent:
    from backend.services.llm.llm_service import LLMService

    llm = LLMService(temperature=0.1, model=model) if model else LLMService(temperature=0.1)
    user_prompt = f"【用户指令】\n{user_instruction.strip()}\n"
    raw = await llm.chat(
        system_prompt=EXPLAIN_SYSTEM,
        user_prompt=user_prompt,
        audit_meta={"kind": "intent_interpreter", "op": "explain_writing_intent"},
    )
    text = raw if isinstance(raw, str) else str(raw or "")
    return parse_explain_intent_json(text)


async def judge_writing_output_vs_instruction(
    user_instruction: str,
    assistant_output: str,
    *,
    model: Optional[str] = None,
) -> RevisionFulfillmentJudgment:
    from backend.services.llm.llm_service import LLMService

    llm = LLMService(temperature=0.1, model=model) if model else LLMService(temperature=0.1)
    user_prompt = (
        f"【用户指令】\n{user_instruction.strip()}\n\n"
        f"【模型输出】\n{(assistant_output or '').strip()[:120000]}\n"
    )
    raw = await llm.chat(
        system_prompt=JUDGE_SYSTEM,
        user_prompt=user_prompt,
        audit_meta={"kind": "intent_interpreter", "op": "judge_revision_fulfillment"},
    )
    text = raw if isinstance(raw, str) else str(raw or "")
    return parse_revision_judgment_json(text)
