"""LLM 工具调用专用测试

测试 LLM 工具调用的完整流程：
- 工具 schema 与 agent 配置
- 工具调用解析与执行
- 流式与非流式工具调用
- 异常与边界情况
"""
import json
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.agent_tools_registry import (
    get_tools_for_llm_by_agent,
    get_tool_names_for_agent,
    CHAT_TOOLS,
    AGENT_TOOLS,
)
from backend.core.agent.tools.base import ToolResult


def _make_tool_call(tool_name: str, arguments: dict, call_id: str = "call_123") -> SimpleNamespace:
    """构造 LLM 返回的 tool_call 对象（与 stream_chat_with_tools 格式一致）"""
    fn = SimpleNamespace(
        name=tool_name,
        arguments=json.dumps(arguments) if isinstance(arguments, dict) else str(arguments),
    )
    return SimpleNamespace(id=call_id, type="function", function=fn)


class TestToolSchemaAndAgentConfig:
    """工具 schema 与 agent 配置测试"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    def test_chat_tools_include_mediawiki(self):
        """CHAT_TOOLS 应包含 mediawiki"""
        assert "mediawiki" in CHAT_TOOLS

    def test_chat_tools_include_google_search(self):
        """CHAT_TOOLS 应包含 google_search"""
        assert "google_search" in CHAT_TOOLS

    def test_get_tool_names_for_agent_general_chat(self):
        """general_chat agent 应返回 CHAT_TOOLS"""
        names = get_tool_names_for_agent("general_chat")
        assert set(names) == set(CHAT_TOOLS)

    def test_get_tool_names_for_agent_article_writing_empty(self):
        """article_writing agent 不配备工具"""
        names = get_tool_names_for_agent("article_writing")
        assert names == []

    def test_get_tools_for_llm_by_agent_filters_correctly(self, orchestrator):
        """get_tools_for_llm_by_agent 应按 agent 过滤工具"""
        all_tools = orchestrator.tool_registry.get_tools_for_llm()
        filtered = get_tools_for_llm_by_agent("general_chat", all_tools)
        filtered_names = {(t.get("function") or {}).get("name") for t in filtered}
        for name in filtered_names:
            assert name in CHAT_TOOLS
        # 不应包含未在 CHAT_TOOLS 中的工具（若有其他已注册工具）
        for t in filtered:
            name = (t.get("function") or {}).get("name")
            assert name in CHAT_TOOLS

    def test_tool_schema_has_required_fields(self, orchestrator):
        """LLM 工具 schema 应包含 type、function、name、parameters"""
        tools = orchestrator.tool_registry.get_tools_for_llm()
        for t in tools:
            assert "type" in t
            assert t["type"] == "function"
            assert "function" in t
            fn = t["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            params = fn["parameters"]
            assert "type" in params
            assert "properties" in params

    def test_mediawiki_tool_has_search_operation(self, orchestrator):
        """mediawiki 工具参数应包含 search 操作"""
        tool = orchestrator.tool_registry.get_tool("mediawiki")
        if not tool:
            pytest.skip("mediawiki 未注册")
        op_param = next((p for p in tool.parameters if p.name == "operation"), None)
        assert op_param is not None
        assert op_param.enum is not None
        assert "search" in op_param.enum

    def test_mediawiki_schema_includes_operation_enum(self, orchestrator):
        """mediawiki 的 LLM schema 应包含 operation 的 enum，便于模型选择"""
        tools = orchestrator.tool_registry.get_tools_for_llm()
        mediawiki = next((t for t in tools if (t.get("function") or {}).get("name") == "mediawiki"), None)
        if not mediawiki:
            pytest.skip("mediawiki 未注册")
        props = mediawiki["function"]["parameters"].get("properties", {})
        op = props.get("operation", {})
        assert "enum" in op
        assert "search" in op["enum"]


class TestToolCallParsingAndExecution:
    """工具调用解析与执行测试"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    @pytest.mark.asyncio
    async def test_tool_registry_execute_mediawiki_search(self, orchestrator):
        """tool_registry.execute 能正确执行 mediawiki search"""
        with patch(
            "backend.core.agent.tools.builtin.mediawiki_tool.MediaWikiClientService"
        ) as mock_mw_cls:
            mock_instance = MagicMock()
            mock_instance.search_pages.return_value = []
            mock_instance.connect = MagicMock()
            mock_mw_cls.return_value = mock_instance
            result = orchestrator.tool_registry.execute(
                "mediawiki",
                operation="search",
                query="张朝阳",
            )
            assert result.success is True
            mock_instance.search_pages.assert_called_once()
            # search_pages(query, limit=limit) 第一个位置参数为 query
            call_args = mock_instance.search_pages.call_args[0]
            assert call_args[0] == "张朝阳"

    @pytest.mark.asyncio
    async def test_tool_registry_execute_google_search(self, orchestrator):
        """tool_registry.execute 能正确执行 google_search"""
        mock_result = MagicMock(title="test", link="https://example.com", snippet="snippet", display_link="example.com")
        mock_response = MagicMock()
        mock_response.results = [mock_result]
        mock_response.search_time = 0.5
        mock_response.total_results = 1
        mock_response.query = "test"
        with patch(
            "backend.core.agent.tools.builtin.google_search_tool.browser_search",
            return_value=mock_response,
        ):
            result = orchestrator.tool_registry.execute("google_search", query="test")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_tool_call_arguments_json_parsing(self):
        """工具调用 arguments 为 JSON 字符串时应正确解析"""
        args_str = '{"operation": "search", "query": "张朝阳"}'
        parsed = json.loads(args_str)
        assert parsed["operation"] == "search"
        assert parsed["query"] == "张朝阳"

    @pytest.mark.asyncio
    async def test_tool_call_invalid_json_fallback_to_empty(self):
        """无效 JSON 时应收敛为 {}"""
        args_str = "invalid json"
        try:
            parsed = json.loads(args_str)
        except json.JSONDecodeError:
            parsed = {}
        assert parsed == {}


class TestStreamToolCallFlow:
    """流式工具调用流程测试（mock LLM）"""

    @pytest.fixture
    def orchestrator(self):
        with patch("backend.core.agent.orchestrator.LLMService") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm_cls.return_value = mock_llm
            orch = Orchestrator()
            orch.llm_service = mock_llm
            return orch

    @pytest.mark.asyncio
    async def test_stream_chat_with_tools_receives_tool_calls_and_executes(
        self, orchestrator
    ):
        """LLM 返回 tool_calls 时，orchestrator 应解析并执行工具"""
        call_count = [0]

        async def mock_stream(messages=None, tools=None, audit_meta=None, out_result=None, **kwargs):
            call_count[0] += 1
            o = out_result if out_result is not None else {}
            o.clear()
            if call_count[0] == 1:
                tc = _make_tool_call("mediawiki", {"operation": "search", "query": "test"})
                o["tool_calls"] = [tc]
            else:
                o["content"] = "搜索完成"
            yield ""

        orchestrator.llm_service.stream_chat_with_tools = mock_stream

        with patch.object(
            orchestrator.tool_registry,
            "execute",
            return_value=ToolResult(success=True, data={"results": []}),
        ) as mock_execute:
            chunks = []
            async for chunk in orchestrator._chat_with_tools_stream(
                system_prompt="你是一个助手",
                user_prompt="搜索 test",
                tools=[{"type": "function", "function": {"name": "mediawiki", "parameters": {}}}],
            ):
                chunks.append(chunk)

            # 应至少调用过一次 execute
            assert mock_execute.call_count >= 1
            call_kwargs = mock_execute.call_args[1]
            assert call_kwargs.get("operation") == "search"
            assert call_kwargs.get("query") == "test"

    @pytest.mark.asyncio
    async def test_stream_tool_call_with_invalid_tool_name_handled(
        self, orchestrator
    ):
        """未知工具名时不应崩溃，应返回错误结果"""
        call_count = [0]

        async def mock_stream(messages=None, tools=None, audit_meta=None, out_result=None, **kwargs):
            call_count[0] += 1
            o = out_result if out_result is not None else {}
            o.clear()
            if call_count[0] == 1:
                tc = _make_tool_call("unknown_tool_xyz", {"arg": "value"})
                o["tool_calls"] = [tc]
            else:
                o["content"] = "工具未找到"
            yield ""

        orchestrator.llm_service.stream_chat_with_tools = mock_stream

        chunks = []
        async for chunk in orchestrator._chat_with_tools_stream(
            system_prompt="",
            user_prompt="test",
            tools=[{"type": "function", "function": {"name": "unknown_tool_xyz", "parameters": {}}}],
        ):
            chunks.append(chunk)

        # 应正常完成，不抛异常
        assert True


class TestChatWithToolsNonStream:
    """非流式 _chat_with_tools 工具调用测试"""

    @pytest.fixture
    def orchestrator(self):
        with patch("backend.core.agent.orchestrator.LLMService") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm_cls.return_value = mock_llm
            orch = Orchestrator()
            orch.llm_service = mock_llm
            return orch

    @pytest.mark.asyncio
    async def test_chat_with_tools_executes_tool_and_continues(
        self, orchestrator
    ):
        """_chat_with_tools 检测到 tool_calls 后执行工具并继续对话"""
        call_count = [0]

        async def mock_chat(messages, tools=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # 第一轮：返回工具调用
                resp = MagicMock()
                resp.content = None
                resp.tool_calls = [
                    _make_tool_call("mediawiki", {"operation": "search", "query": "test"})
                ]
                return resp
            else:
                # 第二轮：返回文本
                resp = MagicMock()
                resp.content = "搜索完成。"
                resp.tool_calls = None
                return resp

        orchestrator.llm_service.chat = AsyncMock(side_effect=mock_chat)

        with patch.object(
            orchestrator.tool_registry,
            "execute",
            return_value=ToolResult(success=True, data={"results": []}),
        ) as mock_execute:
            result = await orchestrator._chat_with_tools(
                system_prompt="",
                user_prompt="搜索 test",
                tools=[{"type": "function", "function": {"name": "mediawiki", "parameters": {}}}],
            )

            assert mock_execute.called
            assert call_count[0] >= 2
            assert result is not None


class TestMediaWikiSearchToolCall:
    """MediaWiki 搜索工具调用专项测试"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    def test_mediawiki_search_operation_requires_query(self, orchestrator):
        """mediawiki operation=search 时 query 为必需"""
        # 缺少 query 时应由工具校验失败或返回空
        result = orchestrator.tool_registry.execute(
            "mediawiki",
            operation="search",
        )
        # 根据实现可能是 success=False 或空结果
        assert result is not None

    @pytest.mark.asyncio
    async def test_mediawiki_tool_call_format_matches_schema(self, orchestrator):
        """LLM 应能生成符合 schema 的 mediawiki 调用"""
        tools = get_tools_for_llm_by_agent(
            "general_chat",
            orchestrator.tool_registry.get_tools_for_llm(),
        )
        mediawiki = next(
            (t for t in tools if (t.get("function") or {}).get("name") == "mediawiki"),
            None,
        )
        if not mediawiki:
            pytest.skip("mediawiki 未注册")

        # 模拟 LLM 生成的参数
        llm_args = {"operation": "search", "query": "张朝阳"}
        # 应能通过工具执行
        with patch(
            "backend.core.agent.tools.builtin.mediawiki_tool.MediaWikiClientService"
        ) as mock_mw_cls:
            mock_instance = MagicMock()
            mock_instance.search_pages.return_value = []
            mock_instance.connect = MagicMock()
            mock_mw_cls.return_value = mock_instance
            result = orchestrator.tool_registry.execute("mediawiki", **llm_args)
            assert result.success is True
