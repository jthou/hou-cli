# 时间：2026-03-22；理由：skill_prematch 与 orchestrator 行为对齐需单测；方法：Mock 技能 + resolve_skill_params_for_execution
from __future__ import annotations

from unittest.mock import MagicMock

from backend.core.agent.skill_prematch import (
    ResolvedSkillParams,
    resolve_skill_params_for_execution,
    skill_registry_match_allowed,
)


def test_skill_registry_match_allowed_false_when_assistants_ctx_and_flag():
    import os

    old = os.environ.get("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS")
    try:
        # 默认（未设置）：写作/工作助手不调用 match
        os.environ.pop("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", None)
        assert skill_registry_match_allowed("article_writing", "x") is False
        assert skill_registry_match_allowed("work_assistant", "x") is False

        os.environ["DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS"] = "false"
        assert skill_registry_match_allowed("article_writing", "x") is True

        os.environ["DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS"] = "true"
        assert skill_registry_match_allowed("article_writing", "x") is False
        assert skill_registry_match_allowed("work_assistant", "x") is False
        assert skill_registry_match_allowed("general_chat", "你好") is False
    finally:
        if old is None:
            os.environ.pop("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", None)
        else:
            os.environ["DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS"] = old


def test_resolve_skill_params_non_general_chat_no_validate():
    skill = MagicMock()
    skill.validate_parameters = MagicMock()

    def extract(t, s):
        return {"a": 1}

    r = resolve_skill_params_for_execution("task", "article_writing", skill, extract)
    assert isinstance(r, ResolvedSkillParams)
    assert r.skill is skill
    assert r.params == {"a": 1}
    assert r.reject_reason is None
    skill.validate_parameters.assert_not_called()


def test_resolve_skill_params_general_chat_validate_fail():
    skill = MagicMock()
    skill.validate_parameters = MagicMock(return_value=(False, "缺少必需参数: input_file"))

    def extract(t, s):
        return {}

    r = resolve_skill_params_for_execution("task", "general_chat", skill, extract)
    assert r.skill is None
    assert r.params is None
    assert "input_file" in (r.reject_reason or "")
