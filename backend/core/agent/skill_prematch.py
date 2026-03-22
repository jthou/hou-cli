# 时间：2026-03-22；理由：process_dynamic 与 stream_process 技能预匹配逻辑需一致；方法：公共函数集中在本模块，Orchestrator 仅编排调用
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from backend.core.agent.general_chat_skill_gate import general_chat_allows_skill_prematch

# 对外 re-export gate，便于只 import skill_prematch 的调用方
__all__ = [
    "disable_skill_prematch_for_assistants",
    "general_chat_allows_skill_prematch",
    "skill_registry_match_allowed",
    "resolve_skill_params_for_execution",
    "ResolvedSkillParams",
]


def disable_skill_prematch_for_assistants(ctx_type: Optional[str]) -> bool:
    """
    写作/工作助手是否在 flag 下跳过 skill_registry.match。
    与 Orchestrator 原 _disable_skill_prematch_for_assistants 行为一致。
    """
    return (
        os.getenv("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", "false").lower() == "true"
        and ctx_type in ("article_writing", "work_assistant")
    )


def skill_registry_match_allowed(ctx_type: Optional[str], task: str) -> bool:
    """
    当前请求是否应调用 skill_registry.match（在 skill_registry 非空且上层未单独处理 assistants 分支的前提下）。

    False：assistants 禁用预匹配，或 general_chat 且未满足门控。
    """
    if disable_skill_prematch_for_assistants(ctx_type):
        return False
    if ctx_type == "general_chat" and not general_chat_allows_skill_prematch(task):
        return False
    return True


@dataclass
class ResolvedSkillParams:
    """技能匹配后：抽取参数 +（general_chat 下）校验；不通过则 skill/params 置空。"""

    skill: Optional[Any]
    params: Optional[Dict[str, Any]]
    reject_reason: Optional[str]


def resolve_skill_params_for_execution(
    task: str,
    ctx_type: Optional[str],
    matched_skill: Any,
    extract_parameters: Callable[[str, Any], Dict[str, Any]],
) -> ResolvedSkillParams:
    """
    从用户任务抽取技能参数；若 context 为 general_chat，则校验必填参数，失败则返回 reject_reason 并清空 skill。
    """
    params = extract_parameters(task, matched_skill)
    if ctx_type != "general_chat":
        return ResolvedSkillParams(skill=matched_skill, params=params, reject_reason=None)
    ok, err = matched_skill.validate_parameters(params)
    if ok:
        return ResolvedSkillParams(skill=matched_skill, params=params, reject_reason=None)
    return ResolvedSkillParams(skill=None, params=None, reject_reason=err or "validate failed")
