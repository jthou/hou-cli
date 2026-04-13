"""DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS：写作助手跳过技能预匹配（编排阶段 1）"""
import os
import pytest
from unittest.mock import AsyncMock, patch

from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.skill_prematch import disable_skill_prematch_for_assistants


def _content_chunks(chunks):
    skip_prefixes = ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__", "__ORCH_TRACE__")
    return [c for c in chunks if not any(c.startswith(p) for p in skip_prefixes)]


class TestDisableSkillPrematchFlag:
    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    def test_helper_only_true_when_env_and_ctx(self, orchestrator):
        with patch.dict(os.environ, {"DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS": "true"}, clear=False):
            assert disable_skill_prematch_for_assistants("article_writing") is True
            assert disable_skill_prematch_for_assistants("work_assistant") is False
            assert disable_skill_prematch_for_assistants("general_chat") is False
            assert disable_skill_prematch_for_assistants(None) is False
        with patch.dict(os.environ, {"DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS": "false"}, clear=False):
            assert disable_skill_prematch_for_assistants("article_writing") is False
        with patch.dict(os.environ, {"DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS": ""}, clear=False):
            assert disable_skill_prematch_for_assistants("article_writing") is True

    @pytest.mark.asyncio
    async def test_stream_work_assistant_skips_skill_registry_match_when_flag(self, orchestrator):
        """生效路径为 _stream_intelligent_orchestration 内 skill_registry.match（非已删除的旧 stream 分支）。"""
        async def mock_stream():
            yield "ok"

        with patch.dict(os.environ, {"DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS": "true"}, clear=False):
            with patch.object(
                orchestrator.skill_registry,
                "match",
                new_callable=AsyncMock,
            ) as mock_match:
                mock_match.side_effect = AssertionError("skill_registry.match 不应被调用")
                with patch.object(
                    orchestrator.llm_service,
                    "stream_chat",
                    return_value=mock_stream(),
                ):
                    chunks = []
                    async for c in orchestrator.stream_process(
                        "整理待办",
                        context={"context_type": "work_assistant", "session_id": "sess_prematch_1"},
                    ):
                        chunks.append(c)
                    mock_match.assert_not_called()
                    assert "ok" in "".join(_content_chunks(chunks))

    @pytest.mark.asyncio
    async def test_stream_article_writing_skips_inner_skill_registry_match(self, orchestrator):
        async def mock_stream():
            yield "x"

        with patch.dict(os.environ, {"DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS": "true"}, clear=False):
            with patch.object(
                orchestrator.skill_registry,
                "match",
                new_callable=AsyncMock,
            ) as mock_match:
                mock_match.side_effect = AssertionError("skill_registry.match 不应被调用")
                with patch.object(
                    orchestrator.llm_service,
                    "stream_chat",
                    return_value=mock_stream(),
                ):
                    chunks = []
                    async for c in orchestrator.stream_process(
                        "写一段引言",
                        context={"context_type": "article_writing", "session_id": "sess_prematch_2"},
                    ):
                        chunks.append(c)
                    mock_match.assert_not_called()
                    assert "x" in "".join(_content_chunks(chunks))

    @pytest.mark.asyncio
    async def test_process_dynamic_skips_match_when_flag_and_article_writing(self, orchestrator):
        with patch.dict(os.environ, {"DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS": "true"}, clear=False):
            with patch.object(
                orchestrator.skill_registry,
                "match",
                new_callable=AsyncMock,
            ) as mock_match:
                mock_match.side_effect = AssertionError("process_dynamic 不应调用 skill_registry.match")
                with patch.object(
                    orchestrator.llm_service,
                    "chat",
                    new_callable=AsyncMock,
                    return_value="done",
                ) as mock_chat:
                    out = await orchestrator.process(
                        "任务",
                        context={"context_type": "article_writing"},
                    )
                    assert out == "done"
                    mock_match.assert_not_called()
                    mock_chat.assert_called()
