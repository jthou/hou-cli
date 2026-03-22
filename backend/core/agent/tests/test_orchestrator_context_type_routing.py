"""Orchestrator stream_process：按 context_type 选用系统提示（与现行单一流式实现一致）

时间：2026-03-13；理由：原测试引用已不存在的 *Agent 属性；方法：patch skill_registry.match + llm_service.stream_chat 断言 system_prompt。
时间：2026-03-13；理由：写作 __CTX_META__ 需编排层回归；方法：收集 __CTX_META__ 帧并解析 JSON。
"""
import json
import os

import pytest
from unittest.mock import AsyncMock, patch

from backend.core.agent.orchestrator import Orchestrator


def _content_text(chunks):
    skip = ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__", "__ORCH_TRACE__")
    return "".join(c for c in chunks if not any(c.startswith(p) for p in skip))


class TestContextTypeRouting:
    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    @pytest.mark.asyncio
    async def test_work_assistant_uses_work_assistant_system_prompt(self, orchestrator):
        async def fake_stream(*args, **kwargs):
            sp = kwargs.get("system_prompt") or ""
            assert "软件架构师的工作助手" in sp
            yield "ok"

        with patch.object(
            orchestrator.skill_registry,
            "match",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch.object(
                orchestrator.llm_service,
                "stream_chat",
                side_effect=fake_stream,
            ):
                chunks = []
                async for c in orchestrator.stream_process(
                    "整理待办",
                    context={"context_type": "work_assistant", "session_id": "sess_route_ws"},
                ):
                    chunks.append(c)
                assert "ok" in _content_text(chunks)

    @pytest.mark.asyncio
    async def test_general_chat_uses_chat_system_prompt(self, orchestrator):
        # general_chat 默认带工具列表时走 _chat_with_tools_stream，不经 llm_service.stream_chat
        def _tools_stream_impl(*args, **kwargs):
            sp = kwargs.get("system_prompt") or ""
            assert "你是一个智能助手" in sp

            async def _gen():
                yield "ok"

            return _gen()

        with patch.object(
            orchestrator.skill_registry,
            "match",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch.object(
                orchestrator,
                "_chat_with_tools_stream",
                side_effect=_tools_stream_impl,
            ):
                chunks = []
                async for c in orchestrator.stream_process(
                    "你好",
                    context={"context_type": "general_chat", "session_id": "sess_route_gc"},
                ):
                    chunks.append(c)
                assert "ok" in _content_text(chunks)

    @pytest.mark.asyncio
    async def test_code_assistant_falls_into_article_writing_branch(self, orchestrator):
        """Orchestrator 无 code_assistant 专用分支：未识别的 context_type 走写文章提示词分支（与实现一致）。"""

        async def fake_stream(*args, **kwargs):
            sp = kwargs.get("system_prompt") or ""
            assert "写作助手" in sp
            yield "ok"

        with patch.object(
            orchestrator.skill_registry,
            "match",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch.object(
                orchestrator.llm_service,
                "stream_chat",
                side_effect=fake_stream,
            ):
                chunks = []
                async for c in orchestrator.stream_process(
                    "写一段 print(1)",
                    context={"context_type": "code_assistant", "session_id": "sess_route_ca"},
                ):
                    chunks.append(c)
                assert "ok" in _content_text(chunks)

    @pytest.mark.asyncio
    async def test_no_context_type_uses_main_flow_stream_chat(self, orchestrator):
        with patch.object(orchestrator.skill_registry, "match", new_callable=AsyncMock, return_value=None):
            async def fake_stream(*args, **kwargs):
                yield "main_flow"

            with patch.object(orchestrator.llm_service, "stream_chat", return_value=fake_stream()):
                chunks = []
                async for c in orchestrator.stream_process("测试任务"):
                    chunks.append(c)
                assert "main_flow" in _content_text(chunks)

    @pytest.mark.asyncio
    async def test_article_writing_stream_yields_ctx_meta(self, orchestrator):
        async def fake_stream(*args, **kwargs):
            sp = kwargs.get("system_prompt") or ""
            assert "写作助手" in sp
            yield "body"

        with patch.dict(os.environ, {"ENABLE_ARTICLE_WRITING_CTX_META": "true"}, clear=False):
            with patch.object(
                orchestrator.skill_registry,
                "match",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch.object(
                    orchestrator.llm_service,
                    "stream_chat",
                    side_effect=fake_stream,
                ):
                    with patch(
                        "backend.core.agent.orchestrator.get_profile_block_for_prompt",
                        return_value="",
                    ):
                        chunks = []
                        async for c in orchestrator.stream_process(
                            "【参考1】摘录\n\n【用户本次提问】\n续写一句",
                            context={
                                "context_type": "article_writing",
                                "session_id": "sess_article_ctx_meta",
                            },
                        ):
                            chunks.append(c)
        meta_chunks = [x for x in chunks if x.startswith("__CTX_META__:")]
        assert len(meta_chunks) >= 1
        payload = json.loads(meta_chunks[0].split(":", 1)[1].strip())
        assert payload.get("strategy") == "article_writing"
        assert payload.get("type") == "context_selection"
        sources = {it.get("source") for it in (payload.get("items") or [])}
        assert "injected_reference" in sources
        assert "user_turn" in sources
        assert "body" in _content_text(chunks)
