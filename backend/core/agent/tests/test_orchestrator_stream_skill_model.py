# 时间：2026-03-21；理由：回归「技能执行前须与 _select_model 一致」；方法：Mock 技能 execute 读取 llm_service.model（设计 docs/design/01-article-writing-agent-and-model-config-design.md §6）。
"""stream_process：技能分支前已 set_model，技能内 llm_service 使用所选模型"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.skills.base import SkillResult


@pytest.mark.asyncio
async def test_stream_process_skill_sees_model_from_select_before_execute():
    orchestrator = Orchestrator()
    orchestrator.enable_planning = False
    orchestrator.enable_evaluation = False

    captured = {}

    async def fake_execute(_params, ctx):
        captured["model_at_execute"] = ctx["llm_service"].model
        return SkillResult(success=True, data={"ok": True})

    fake_skill = MagicMock()
    fake_skill.name = "writing_profile_summary"
    fake_skill.parameters = []
    fake_skill.execute = AsyncMock(side_effect=fake_execute)

    with patch.object(orchestrator.skill_registry, "match", new_callable=AsyncMock, return_value=fake_skill):
        with patch.object(orchestrator, "_select_model", new_callable=AsyncMock, return_value="expected-model-for-skill"):
            with patch.object(orchestrator.memory_flush_trigger, "should_flush", return_value=False):
                async for _ in orchestrator.stream_process(
                    "测试任务以触发技能路径",
                    context={
                        "session_id": "test_stream_skill_model_sess",
                        "context_type": "article_writing",
                    },
                ):
                    pass

    assert captured.get("model_at_execute") == "expected-model-for-skill"
    fake_skill.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_stream_process_non_skill_path_still_single_select():
    """未命中技能时仍只应产生一次 _select_model（主路径不再重复调用）"""
    orchestrator = Orchestrator()
    orchestrator.enable_planning = False
    orchestrator.enable_evaluation = False

    async def mock_stream():
        yield "x"

    select_mock = AsyncMock(return_value="m1")

    with patch.object(orchestrator.skill_registry, "match", new_callable=AsyncMock, return_value=None):
        with patch.object(orchestrator, "_select_model", select_mock):
            with patch.object(orchestrator.memory_flush_trigger, "should_flush", return_value=False):
                with patch.object(orchestrator.llm_service, "stream_chat", return_value=mock_stream()):
                    async for _ in orchestrator.stream_process(
                        "你好",
                        context={
                            "session_id": "test_stream_no_skill_sess",
                            "context_type": "article_writing",
                        },
                    ):
                        pass

    assert select_mock.await_count == 1
