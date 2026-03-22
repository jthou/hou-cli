"""SkillRegistry.match 结构化日志（编排阶段 0，SKILL_MATCH_TRACE）"""
import json
import logging
import pytest
from unittest.mock import AsyncMock, patch

from backend.core.agent.skills.base import Skill, SkillResult
from backend.core.agent.skills.registry import SkillRegistry, SKILL_MATCH_TRACE_PREFIX


class _DummySkill(Skill):
    async def execute(self, parameters, context=None):
        return SkillResult(success=True)


def _trace_payloads(caplog):
    out = []
    for rec in caplog.records:
        if rec.levelno >= logging.INFO and SKILL_MATCH_TRACE_PREFIX in (rec.getMessage() or ""):
            msg = rec.getMessage()
            idx = msg.find(SKILL_MATCH_TRACE_PREFIX)
            if idx >= 0:
                json_part = msg[idx + len(SKILL_MATCH_TRACE_PREFIX) :].strip()
                out.append(json.loads(json_part))
    return out


@pytest.mark.asyncio
async def test_trace_llm_matched_includes_context_type(caplog):
    caplog.set_level(logging.INFO)
    reg = SkillRegistry()
    reg.register(_DummySkill(name="dummy_skill", description="测试技能 dummy"))

    with patch("backend.services.llm.llm_service.LLMService") as MockLLM:
        MockLLM.return_value.chat = AsyncMock(return_value='{"skill_name": "dummy_skill"}')
        skill = await reg.match("帮我用 dummy", context_type="general_chat")
    assert skill is not None and skill.name == "dummy_skill"
    payloads = _trace_payloads(caplog)
    assert len(payloads) == 1
    assert payloads[0]["llm_outcome"] == "matched"
    assert payloads[0]["keyword_fallback"] is False
    assert payloads[0]["result_skill"] == "dummy_skill"
    assert payloads[0]["context_type"] == "general_chat"


@pytest.mark.asyncio
async def test_trace_llm_no_skill(caplog):
    caplog.set_level(logging.INFO)
    reg = SkillRegistry()
    reg.register(_DummySkill(name="dummy_skill", description="测试"))

    with patch("backend.services.llm.llm_service.LLMService") as MockLLM:
        MockLLM.return_value.chat = AsyncMock(return_value='{"skill_name": null}')
        skill = await reg.match("随便聊聊")
    assert skill is None
    payloads = _trace_payloads(caplog)
    assert len(payloads) == 1
    assert payloads[0]["llm_outcome"] == "no_skill"
    assert payloads[0]["result_skill"] is None


@pytest.mark.asyncio
async def test_trace_parse_error_then_keyword_no_match(caplog):
    caplog.set_level(logging.INFO)
    reg = SkillRegistry()
    reg.register(_DummySkill(name="dummy_skill", description="仅用于注册列表"))

    with patch("backend.services.llm.llm_service.LLMService") as MockLLM:
        MockLLM.return_value.chat = AsyncMock(return_value="not valid json {{{")
        skill = await reg.match("xyz_no_keyword_match_12345", context_type=None)
    assert skill is None
    payloads = _trace_payloads(caplog)
    assert payloads[0]["llm_outcome"] == "parse_error"
    assert payloads[-1]["keyword_fallback"] is True
    assert payloads[-1]["keyword_outcome"] == "no_match"
