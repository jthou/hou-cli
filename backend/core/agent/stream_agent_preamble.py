"""
流式回复开场白：身份标识 + 可选编排一行说明。

时间：2026-03-21；理由：产品要求「开始输出时标明 Agent 身份；编排侧给出路由摘要」；方法：默认 off，通过 STREAM_AGENT_PREAMBLE 或 context["stream_agent_preamble"] 开启，避免扰动未显式开启的会话与单测。
"""
from __future__ import annotations

import os
from typing import Dict, Iterator, Literal, Optional

StreamPreambleMode = Literal["off", "identity", "full"]


def resolve_stream_agent_preamble_mode(context: Optional[Dict]) -> StreamPreambleMode:
    ctx = context or {}
    raw = ctx.get("stream_agent_preamble")
    if isinstance(raw, str):
        r = raw.lower().strip()
        if r in ("off", "none", "false", "0", ""):
            return "off"
        if r == "full":
            return "full"
        if r in ("identity", "on", "true", "1", "yes"):
            return "identity"
    env = (os.getenv("STREAM_AGENT_PREAMBLE") or os.getenv("STREAM_AGENT_PREAMBLE_MODE") or "off").lower().strip()
    if env == "full":
        return "full"
    if env in ("identity", "on", "true", "1", "yes"):
        return "identity"
    return "off"


def _role_label(
    ctx_type: Optional[str],
    is_general_chat: bool,
) -> str:
    if is_general_chat:
        return "通用对话Agent"
    if ctx_type == "article_writing":
        return "写作助手Agent"
    return "写作助手Agent"


def iter_stream_preamble_text(
    mode: StreamPreambleMode,
    *,
    branch: Literal["skill", "llm_tools", "llm_plain"],
    ctx_type: Optional[str],
    is_general_chat: bool,
    matched_skill_name: Optional[str],
    selected_model: Optional[str],
    skill_prematch_skipped: bool,
    tools_count: int,
) -> Iterator[str]:
    if mode == "off":
        return
    model_s = (selected_model or "默认模型").strip()

    if branch == "skill" and matched_skill_name:
        yield f"【我是技能执行Agent · {matched_skill_name}】\n\n"
        if mode == "full":
            yield (
                "【编排说明】UnifiedOrchestrator 路由：技能预匹配命中，本段正文由该技能执行管线生成（非主对话模板直出）。\n\n"
            )
        return

    role = _role_label(ctx_type, is_general_chat)
    yield f"【我是{role}】\n\n"

    if mode != "full":
        return

    orch = "【我是编排协调Agent】"
    parts = [
        f"context_type={ctx_type or '（未标注）'}",
        f"选用模型={model_s}",
    ]
    if skill_prematch_skipped:
        parts.append("技能预匹配=按配置跳过（写作助手关抢答）")
    else:
        parts.append("技能预匹配=未命中，进入主对话/工具路径")
    if branch == "llm_tools":
        parts.append(f"工具数={tools_count}，将经 LLM 工具循环后流式输出")
    else:
        parts.append("无可用工具，单轮 stream_chat 流式输出")
    yield f"{orch} " + "；".join(parts) + "。\n\n"
