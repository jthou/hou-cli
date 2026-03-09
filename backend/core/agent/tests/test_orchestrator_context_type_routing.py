"""Orchestrator context_type 路由测试：验证 work_assistant/general_chat/code_assistant 正确分发"""
import pytest
from unittest.mock import patch, MagicMock
from backend.core.agent.orchestrator import Orchestrator


async def _fake_stream_ok(token: str):
    """返回产出单个 token 的 async generator（stream_process 需返回 async generator）"""
    yield token


class TestContextTypeRouting:
    """验证 stream_process 根据 context_type 正确路由到对应 Agent"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    @pytest.mark.asyncio
    async def test_code_assistant_routes_to_agent(self, orchestrator):
        """context_type=code_assistant 应路由到 code_assistant_agent"""
        with patch.object(
            orchestrator.code_assistant_agent,
            "stream_process",
            new=MagicMock(return_value=_fake_stream_ok("code_assistant_ok")),
        ) as mock_stream:
            chunks = []
            async for c in orchestrator.stream_process(
                "写一段 print(1) 执行看看",
                context={"context_type": "code_assistant"},
            ):
                chunks.append(c)
            mock_stream.assert_called_once()
            # stream_process(task, context, delegate=self) -> args=(task, context), kwargs={delegate: ...}
            call_args = mock_stream.call_args
            context = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("context", {})
            assert (context or {}).get("context_type") == "code_assistant"
            content = "".join(c for c in chunks if not any(c.startswith(p) for p in ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__")))
            assert "code_assistant_ok" in content

    @pytest.mark.asyncio
    async def test_work_assistant_routes_to_agent(self, orchestrator):
        """context_type=work_assistant 应路由到 work_assistant_agent"""
        with patch.object(
            orchestrator.work_assistant_agent,
            "stream_process",
            new=MagicMock(return_value=_fake_stream_ok("work_assistant_ok")),
        ) as mock_stream:
            chunks = []
            async for c in orchestrator.stream_process(
                "帮我整理待办",
                context={"context_type": "work_assistant"},
            ):
                chunks.append(c)
            mock_stream.assert_called_once()
            content = "".join(c for c in chunks if not any(c.startswith(p) for p in ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__")))
            assert "work_assistant_ok" in content

    @pytest.mark.asyncio
    async def test_general_chat_routes_to_agent(self, orchestrator):
        """context_type=general_chat 应路由到 general_chat_agent"""
        with patch.object(
            orchestrator.general_chat_agent,
            "stream_process",
            new=MagicMock(return_value=_fake_stream_ok("general_chat_ok")),
        ) as mock_stream:
            chunks = []
            async for c in orchestrator.stream_process(
                "今天天气怎么样",
                context={"context_type": "general_chat"},
            ):
                chunks.append(c)
            mock_stream.assert_called_once()
            content = "".join(c for c in chunks if not any(c.startswith(p) for p in ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__")))
            assert "general_chat_ok" in content

    @pytest.mark.asyncio
    async def test_no_context_type_uses_main_flow(self, orchestrator):
        """无 context_type 时走主流程（技能匹配/写作等），调用 stream_chat"""
        with patch.object(orchestrator.llm_service, "stream_chat") as mock_stream:
            async def fake_stream(*args, **kwargs):
                yield "main_flow"

            mock_stream.return_value = fake_stream()
            chunks = []
            async for c in orchestrator.stream_process("测试任务"):
                chunks.append(c)
            content = "".join(c for c in chunks if not any(c.startswith(p) for p in ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__")))
            assert "main_flow" in content
            mock_stream.assert_called()
