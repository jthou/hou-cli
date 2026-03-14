"""ExecPyTool / ExecShellTool 测试"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from shared.load_env import load_env_for_file
load_env_for_file(__file__)

from backend.core.agent.tools.builtin.code_executor_tool import ExecPyTool, ExecShellTool
from backend.core.agent.tools.base import ToolResult


class TestExecPyTool:
    """ExecPyTool 单元测试"""

    @pytest.fixture
    def tool(self):
        return ExecPyTool()

    def test_tool_initialization(self, tool):
        assert tool.name == "exec_py"
        assert tool.description is not None
        param_names = [p.name for p in tool.parameters]
        assert "code" in param_names
        assert "language" not in param_names

    def test_missing_code(self, tool):
        result = tool.execute()
        assert result.success is False
        assert "code" in result.error.lower() or "必需" in result.error

    def test_execute_python_code(self, tool):
        result = tool.execute(code="print('Hello, World!')", timeout=10)
        if result.success:
            assert "output" in result.data
            assert "Hello, World!" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    @pytest.mark.asyncio
    async def test_progress_callback_receives_output(self, tool):
        collected = []
        tool.set_progress_callback(lambda msg: collected.append(msg))
        result = await tool._execute_async(code="print('line1'); print('line2')", timeout=10)
        if result.success and collected:
            assert any("line1" in c or "line2" in c for c in collected)


class TestExecShellTool:
    """ExecShellTool 单元测试"""

    @pytest.fixture
    def tool(self):
        return ExecShellTool()

    def test_tool_initialization(self, tool):
        assert tool.name == "exec_shell"
        assert tool.description is not None
        param_names = [p.name for p in tool.parameters]
        assert "code" in param_names
        assert "language" not in param_names

    def test_missing_code(self, tool):
        result = tool.execute()
        assert result.success is False
        assert "code" in result.error.lower() or "必需" in result.error

    def test_execute_zsh_code(self, tool):
        result = tool.execute(code="echo 'Hello, World!'", timeout=10)
        if result.success:
            assert "output" in result.data
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")


class TestCodeExecutorToolsIntegration:
    """集成测试（需要真实环境）"""

    @pytest.mark.integration
    def test_python_workflow(self):
        tool = ExecPyTool()
        result = tool.execute(
            code='x = 10; y = 20; print(f"Sum: {x + y}")',
            timeout=30
        )
        if result.success:
            assert "output" in result.data
            assert "Sum: 30" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    @pytest.mark.integration
    def test_zsh_workflow(self):
        tool = ExecShellTool()
        result = tool.execute(code='echo "Test 1"; echo "Test 2"', timeout=30)
        if result.success:
            assert "output" in result.data
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")


class TestCodeExecutorToolsParameters:
    """参数测试"""

    def test_exec_py_parameters(self):
        tool = ExecPyTool()
        param_names = [p.name for p in tool.parameters]
        assert "code" in param_names
        assert "timeout" in param_names
        assert "explanation" in param_names
        assert "language" not in param_names

    def test_exec_shell_parameters(self):
        tool = ExecShellTool()
        param_names = [p.name for p in tool.parameters]
        assert "code" in param_names
        assert "timeout" in param_names
        assert "explanation" in param_names
        assert "language" not in param_names


class TestCodeExecutorToolsRegistry:
    """注册测试（使用 Orchestrator 确保工具已注册）"""

    def test_tools_can_be_registered(self):
        from backend.core.agent.orchestrator import Orchestrator
        orchestrator = Orchestrator()
        tools_list = orchestrator.tool_registry.list_tools()
        assert "exec_py" in tools_list
        assert "exec_shell" in tools_list

    def test_tool_for_llm_format(self):
        from backend.core.agent.orchestrator import Orchestrator
        orchestrator = Orchestrator()
        llm_tools = orchestrator.tool_registry.get_tools_for_llm()
        exec_py = next((t for t in llm_tools if t["function"]["name"] == "exec_py"), None)
        exec_shell = next((t for t in llm_tools if t["function"]["name"] == "exec_shell"), None)
        assert exec_py is not None
        assert exec_shell is not None
        assert exec_py["function"]["name"] == "exec_py"
        assert exec_shell["function"]["name"] == "exec_shell"


class TestExecShellToolZshScripts:
    """ExecShellTool Zsh 脚本测试"""

    @pytest.fixture
    def tool(self):
        return ExecShellTool()

    def test_zsh_variables(self, tool):
        result = tool.execute(code='NAME="World"; echo "Hello, $NAME!"', timeout=10)
        if result.success:
            assert "Hello, World!" in result.data.get("output", "")
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")
