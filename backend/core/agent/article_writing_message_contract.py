"""
写作助手：发往模型的 **user 消息** 中与「参考块 + 用户句」及 **可拼接的注入片段** 相关的契约与生成函数。

时间：2026-03-21；理由：消除 CLI、测试与 orchestrator 重复，并与 UI 单次发送逻辑一致；
方法：字符串与拼接规则须与 frontend/react-app/src/utils/referenceUtils.js 保持同步（改一侧必改另一侧）。

时间：2026-04-04；理由：模块职责梳理；方法：本文件仅保留「消息形状 + 写作向注入」；**会话级 workflow 判定**（如 doc_coauthoring）见 `article_writing_workflow.py`。

分层（便于判断「是否与公众号长文新写/改稿相关」）：
1. **参考块契约**：`USER_QUESTION_MARKER`、`REFERENCE_INTRO`、`format_reference_context`、`build_message_for_model` 等——与前端一致，任意带参考的写作请求都需要。
2. **长文新写辅助注入**：`build_article_word_count_constraint_injection`、`build_article_sectioning_hint_injection`——落实用户明确字数/长文结构意图，服务「新写长文」。
3. **长文改稿辅助注入**：`build_article_draft_scope_prefix`、`build_bracketed_revision_opinion_injection`——锚定右侧草稿与修改意见，服务「改稿」。

说明：
- 无参考块（或全部 content 为空）时，消息体 **仅** 为用户输入，不含「【用户本次提问】」前缀（与 ArticleWriting.jsx 一致）。
- 有参考时：format_reference_context + 【用户本次提问】\\n + 用户输入。
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Optional

# 用户提出「N 字左右」时与注入提醒一致的浮动比例（时间：2026-03-21；理由：模型常明显偏短；方法：编排层追加可执行区间）
_WORD_COUNT_AROUND_RATIO = 0.15
_WORD_COUNT_MIN_DIGITS = 3
_WORD_COUNT_MAX_DIGITS = 5

# ---------------------------------------------------------------------------
# 与 referenceUtils.js 顶部常量一致（同步修改）
# ---------------------------------------------------------------------------
USER_QUESTION_MARKER = "【用户本次提问】"

# 时间：2026-04-04；理由：用户常在正文内嵌（修改意见：…）；方法：引导模型把括号内意见当硬约束，与 JS referenceUtils 同步
# 时间：2026-04-04；理由：范文+修改意见场景模型易脱离意见发挥；方法：明确「先落实意见→再梳理」，禁止编造扩写
REFERENCE_INTRO = (
    "以下是用户提供的参考资料（可能含待改范文、素材或链接稿）。请结合用户本次提问使用。"
    "若用户给出修改意见（含提问或资料中的「（修改意见：…）」「(修改意见：…)」等），须**先严格按修改意见逐条落实**，再在**原文事实与论点边界内**做必要梳理（层次、衔接、删冗、统一人称术语）；"
    "**禁止**脱离范文与意见编造内容、虚构案例，或擅自扩写用户未要求的段落与章节；括号内修订说明与显式「修改意见」清单同等效力。"
    "若括号紧跟在文章标题（如 `# 标题`）之后，仍须完整阅读并落实，不得以「在标题旁」为由跳过。\n\n"
)

# ---------------------------------------------------------------------------
# 参考块与用户句（与 referenceUtils.js 同步）
# ---------------------------------------------------------------------------

# CLI：显式表示「无参考」的占位串，不生成参考块（与 UI 空面板一致）
_NO_REFERENCE_SENTINELS = frozenset({"", "(无)", "（无）"})


def is_no_reference_placeholder(value: Optional[str]) -> bool:
    """是否与 UI「未添加参考块」等价（不拼参考前缀）。"""
    if value is None:
        return True
    return value.strip() in _NO_REFERENCE_SENTINELS


def _block_content(block: Mapping[str, Any]) -> str:
    return str(block.get("content") or "").strip()


def _block_title(block: Mapping[str, Any]) -> str:
    return str(block.get("title") or "").strip()


def normalize_reference_blocks(
    blocks: Optional[Iterable[Mapping[str, Any]]],
) -> list[dict[str, str]]:
    """与 JS formatReferenceContext 同样过滤：仅保留 content 非空的块。"""
    out: list[dict[str, str]] = []
    for b in blocks or []:
        content = _block_content(b)
        if not content:
            continue
        out.append({"title": _block_title(b), "content": content})
    return out


def format_reference_context(blocks: Optional[Iterable[Mapping[str, Any]]]) -> str:
    """
    等价于 referenceUtils.formatReferenceContext：
    无有效块时返回空串。
    """
    trimmed = normalize_reference_blocks(blocks)
    if not trimmed:
        return ""
    parts: list[str] = []
    for idx, b in enumerate(trimmed):
        title = b["title"]
        header = f"【参考{idx + 1}：{title}】" if title else f"【参考{idx + 1}】"
        parts.append(f"{header}\n{b['content']}")
    body = "\n\n".join(parts)
    return f"{REFERENCE_INTRO}{body}\n\n---\n\n"


def build_message_for_model(
    reference_blocks: Optional[Iterable[Mapping[str, Any]]],
    user_text: str,
) -> str:
    """
    等价于 ArticleWriting / WorkAssistant / GeneralChat 中：
    referenceContext ? `${referenceContext}【用户本次提问】\\n${text}` : text
    """
    text = (user_text or "").strip()
    ref = format_reference_context(reference_blocks)
    if not ref:
        return text
    return f"{ref}{USER_QUESTION_MARKER}\n{text}"


# ---------------------------------------------------------------------------
# 长文新写：字数与分节（仅在有明确 task 信号时注入，见各函数 docstring）
# ---------------------------------------------------------------------------


def build_article_word_count_constraint_injection(task: str) -> str:
    """
    从 user/task 全文检出明确字数要求，生成追加到写作助手 user 消息末尾的短提醒（强制遵守）。

    时间：2026-03-21；理由：用户反馈「2000字左右」仍输出约 1600 字；方法：正则检出 + 给出上下限汉字数区间。
    仅在有把握匹配时返回非空，避免无指令兜底。
    """
    t = task or ""
    if not t.strip():
        return ""

    d = rf"(\d{{{_WORD_COUNT_MIN_DIGITS},{_WORD_COUNT_MAX_DIGITS}}})"

    # 「N 字左右」：取最后一次出现（靠后的往往是正文要求）
    around_n: Optional[int] = None
    for m in re.finditer(rf"{d}\s*字左右", t):
        around_n = int(m.group(1))
    if around_n is not None:
        lo = max(1, int(round(around_n * (1.0 - _WORD_COUNT_AROUND_RATIO))))
        hi = int(round(around_n * (1.0 + _WORD_COUNT_AROUND_RATIO)))
        return (
            "【系统检出·用户字数要求】\n"
            f"用户提出约 **{around_n} 字**（「左右」）：请以 {around_n} 字为目标篇幅，"
            f"正文总字数建议落在 **{lo}～{hi} 字**（含汉字、字母、数字与标点），"
            f"**不得明显偏短**（低于 {lo} 字视为未遵守用户格式要求）。"
        )

    m = re.search(rf"约\s*{d}\s*字", t)
    if m:
        n = int(m.group(1))
        lo = max(1, int(round(n * (1.0 - _WORD_COUNT_AROUND_RATIO))))
        hi = int(round(n * (1.0 + _WORD_COUNT_AROUND_RATIO)))
        return (
            "【系统检出·用户字数要求】\n"
            f"用户提出 **约 {n} 字**：请以 {n} 字为目标，正文建议 **{lo}～{hi} 字**，不得明显偏短。"
        )

    m = re.search(rf"{d}\s*字以内", t)
    if m:
        n = int(m.group(1))
        return (
            "【系统检出·用户字数要求】\n"
            f"用户要求 **{n} 字以内**：正文总字数不得超过 **{n} 字**（含汉字、字母、数字与标点）。"
        )

    m = re.search(rf"不少于\s*{d}\s*字", t)
    if m:
        n = int(m.group(1))
        return (
            "【系统检出·用户字数要求】\n"
            f"用户要求 **不少于 {n} 字**：正文总字数须 **≥ {n} 字**（含汉字、字母、数字与标点）。"
        )

    return ""


def _user_forbids_markdown_sectioning(task: str) -> bool:
    """用户明确要求不要标题/分段时，不注入长文分节提示。"""
    t = task or ""
    keys = (
        "不要小标题",
        "不要标题",
        "不要分段",
        "一段话",
        "只要一段",
        "不分段",
        "单段",
        "无小标题",
    )
    return any(k in t for k in keys)


def _user_forbids_conclusion_heading(task: str) -> bool:
    t = task or ""
    return any(
        k in t
        for k in ("不要结论", "不要总结", "无需结论", "省略结论", "不写结论")
    )


def _max_numeric_word_target(task: str) -> int:
    """从 task 中取出「字左右 / 约N字」等目标字数的最大值，供长文判定。"""
    t = task or ""
    best = 0
    d = rf"(\d{{{_WORD_COUNT_MIN_DIGITS},{_WORD_COUNT_MAX_DIGITS}}})"
    for m in re.finditer(rf"{d}\s*字左右", t):
        best = max(best, int(m.group(1)))
    m = re.search(rf"约\s*{d}\s*字", t)
    if m:
        best = max(best, int(m.group(1)))
    m = re.search(rf"不少于\s*{d}\s*字", t)
    if m:
        best = max(best, int(m.group(1)))
    return best


def _implies_long_form_article_request(task: str) -> bool:
    t = task or ""
    if "新写全文" in t or "重写全文" in t:
        return True
    if re.search(r"写[一1]?篇", t) and ("文章" in t or "全文" in t):
        return True
    if _max_numeric_word_target(t) >= 800:
        return True
    return False


def build_article_sectioning_hint_injection(task: str) -> str:
    """
    长文时注入分节版式建议（引言 + 编号小节 + 结论），避免通篇巨型加粗段。

    时间：2026-03-21；理由：用户反馈 2000 字长文版式丑、缺层次；方法：与字数检出类似，追加【系统检出·长文版式】；
    若用户禁止分节/结论则跳过（无指令不强行兜底）。
    """
    t = task or ""
    if not t.strip():
        return ""
    if _user_forbids_markdown_sectioning(t):
        return ""
    if not _implies_long_form_article_request(t):
        return ""

    if _user_forbids_conclusion_heading(t):
        tail = (
            "用户不要求单独结论标题时，**不要**添加 `## 结论`；在最后一节末自然收束即可。"
        )
    else:
        tail = (
            "末尾请设 `## 结论`，用 **1～2 段** 短收束（提炼观点即可，勿再展开新的大分论点）。"
        )

    return (
        "【系统检出·长文版式】\n"
        "检测到**完整长文**需求。请用 Markdown **`##` 二级标题** 分节，**全文只用一种编号风格**，建议：\n"
        "- `## 引言`：背景与问题界定，**控制篇幅**，勿写成整节长文；\n"
        "- 主体：按用户主题拆成 **至少 4 个** 同级小节，推荐使用 `## 01 …` `## 02 …` … **或** `## 一、…` `## 二、…`（二选一，勿混用），"
        "每节内再分段论述，**禁止**单节仅一条跨屏 `**加粗**`；\n"
        f"- {tail}\n"
        "**禁止**整篇只有 2～3 个超长加粗段落；小节标题应能概括本节唯一主旨。"
    )


# ---------------------------------------------------------------------------
# 长文改稿：草稿锚点与修改意见（编排层通常：草稿前缀 → 画像 → task → 字数/分节/括号注入）
# ---------------------------------------------------------------------------


def build_article_draft_scope_prefix(current_article: Optional[str]) -> str:
    """
    写作流式分支：当右侧草稿非空时，前置注入「改稿范围」+ 全文草稿，避免模型忽略局部意见而整篇重答。

    时间：2026-03-13；理由：此前 stream_process 未注入 get_current_article；且 system 曾写「未要求 patch 即全文」误导模型；
    方法：有草稿时在 user 前部插入本段，由 system 【输出规则】与之对齐。
    时间：2026-04-04；理由：用户反馈「润色全文」仍被当成整篇重贴；方法：明确否定以优化为名的全文替换，并强调括号修改意见。
    """
    body = (current_article or "").strip()
    if not body:
        return ""
    return (
        "【改稿范围（须遵守）】\n"
        "下文【当前文章（右侧草稿）】区块为作者当前成稿。"
        "**你必须以本条 user 消息中「【用户本次提问】」之后的内容为本次唯一执行指令**（若无该标记，则以 user 末尾用户输入为准）。\n"
        "- **默认（有草稿时）**：**局部优先**——只落实该指令：答疑、改写用户点名的段落/句子/小节，或给出**可粘贴**的局部 Markdown 替换块（须说明对应标题或原文位置）；"
        "若改动范围清晰且适合 diff，**优先**输出 ```patch``` 代码块（unified diff），diff 上下文须与草稿**逐字一致**。\n"
        "- **禁止**：在用户**未明确要求全文级重写**时，用「优化全文」「通篇润色」「整体重写一版」等理由输出整篇新稿顶替草稿；"
        "也**禁止**在用户仅要求「按括号/修改意见改」时，擅自改动未被意见点名的章节结构或大量未涉及正文。\n"
        "- **全文输出**仅当用户**明确**表达全文重写意图，例如：「重写全文」「整篇重写」「全文改写」「重新写一篇完整稿」「整篇按下面意见改」「推倒重来整篇」等；"
        "若仅「改第二段」「润色开头」「这段太啰嗦」「只按修改意见」等，**不是**全文重写。\n\n"
        f"【当前文章（右侧草稿）】\n{body}\n\n---\n\n"
    )


# 正文/提问中常见的括号修订标记（半角/全角）
_BRACKETED_REVISION_HEAD_RE = re.compile(
    r"[（(]\s*(修改意见|修订意见|修改说明)\s*[:：]?",
    re.MULTILINE,
)

# 时间：2026-04-04；理由：用户常把「（修改意见：…）」紧接在标题后，模型扫读易漏；方法：摘出首段括号内正文再注入 user，强制对齐
_BRACKETED_OPINION_BODY_RE = re.compile(
    r"[（(]\s*修改意见\s*[：:]\s*(.+?)\s*[）)]",
    re.DOTALL,
)
_BRACKETED_OPINION_BODY_MAX_LEN = 1200


def _extract_first_bracketed_revision_opinion_body(task: str) -> str:
    """从 task 中取出首处「（修改意见：…）」内正文，供注入复述；无则空串。"""
    t = task or ""
    m = _BRACKETED_OPINION_BODY_RE.search(t)
    if not m:
        return ""
    body = (m.group(1) or "").strip()
    if len(body) > _BRACKETED_OPINION_BODY_MAX_LEN:
        body = body[:_BRACKETED_OPINION_BODY_MAX_LEN].rstrip() + "…"
    return body


def _task_implies_revision_opinions(task: str) -> bool:
    """是否应注入「修改意见落实」提醒：括号头或文中出现「修改意见」三字（时间：2026-04-04；理由：用户常不用括号标注）。"""
    t = task or ""
    if not t.strip():
        return False
    if _BRACKETED_REVISION_HEAD_RE.search(t) is not None:
        return True
    return "修改意见" in t


def build_bracketed_revision_opinion_injection(task: str) -> str:
    """
    当 task 中含「修改意见」或「（修改意见：…）」等修订提示时，向 user 末尾追加硬提醒，与 system 【修改意见】规则对齐。

    时间：2026-04-04；理由：模型易忽略修改意见或改稿时整篇重贴；方法：括号正则或「修改意见」三字检出（无匹配则空串，不兜底）。
    时间：2026-04-04；理由：用户可无括号仅写「修改意见」；方法：_task_implies_revision_opinions 并入三字匹配。
    """
    t = task or ""
    if not t.strip():
        return ""
    if not _task_implies_revision_opinions(t):
        return ""
    quoted = _extract_first_bracketed_revision_opinion_body(t)
    quote_block = ""
    if quoted:
        quote_block = (
            "\n\n【系统摘录·括号内修改意见正文（须逐字义落实，禁止概括替换）】\n"
            f"「{quoted}」\n"
            "你必须把其中**全部叙事要素**写进用户点名的段落（如「重写第一段」则仅重写开篇，且开篇须含）："
            "用户写明的人称/视角、**从业年限**、**时间锚点**（如「一年前」）、**具体决策**（如「决定拥抱 AI 编程」）等；"
            "**禁止**改写成泛泛的「开发者」「业界」「茶余饭后」等**抹掉上述要素**的套话开篇。\n"
        )
    return (
        "【系统检出·修改意见落实】\n"
        "检测到 **「修改意见」** 相关指令（含文中 **（修改意见：…）**、**(修改意见：…)**、**（修订意见：…）** 等括号说明，或**未加括号**但出现「修改意见」字样）。你必须：\n"
        "1. **先**逐条落实修改意见（含参考块内范文上的意见），**再**在必要处梳理成稿；**禁止**借「优化」「润色」「梳理」之名新增用户未要求的论点、案例或章节。\n"
        "2. **逐条**落实，不得遗漏、不得合并曲解；若意见写在括号占位里，成稿中**删除**已处理的括号提示行/括号段（勿保留「（修改意见：…）」占位）。\n"
        "3. 若本条 user 同时含【当前文章（右侧草稿）】且用户**未**明示全文重写：默认只改与这些意见相关的句段，**保留**其余结构与表述，**禁止**为「文风统一」整篇重贴。\n"
        "4. 若用户明示「只改修改意见」「只改括号意见」「不要动其它段落」，则**仅**处理所列意见涉及之处，其它一字不改（除非某意见本身要求动其它处）。\n"
        "5. 若修改意见紧接在标题 `# …` 之后、与正文在同一段提问里，**不得以「在标题旁」为由忽略**——仍须完整阅读括号内全文并落实。"
        f"{quote_block}"
    )
