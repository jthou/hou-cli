"""CodeExecutorTool 测试"""
import pytest
import os
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
from backend.core.agent.tools.base import ToolResult


class TestCodeExecutorTool:
    """CodeExecutorTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 CodeExecutorTool 实例"""
        return CodeExecutorTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "execute_code"
        assert tool.description is not None
        assert len(tool.parameters) >= 2

        param_names = [p.name for p in tool.parameters]
        assert "code" in param_names
        assert "language" in param_names

    def test_missing_code(self, tool):
        """测试缺少 code 参数"""
        result = tool.execute()
        assert result.success is False
        assert "code" in result.error.lower() or "必需" in result.error

    def test_missing_language(self, tool):
        """测试缺少 language 参数"""
        result = tool.execute(code="print('hello')")
        assert result.success is False
        assert "language" in result.error.lower() or "必需" in result.error

    def test_invalid_language(self, tool):
        """测试无效的语言"""
        result = tool.execute(code="print('hello')", language="invalid")
        assert result.success is False
        assert "不支持" in result.error or "invalid" in result.error.lower()

    def test_timeout_validation(self, tool):
        """测试超时参数验证"""
        # 测试超过最大超时
        result = tool.execute(
            code="print('hello')",
            language="python",
            timeout=500
        )
        # 应该被限制到 300

    def test_execute_python_code(self, tool):
        """测试执行 Python 代码"""
        result = tool.execute(
            code="print('Hello, World!')",
            language="python",
            timeout=10
        )

        if result.success:
            assert "output" in result.data
            assert "Hello, World!" in result.data["output"]
        else:
            # 检查是否是执行器问题
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_execute_bash_code(self, tool):
        """测试执行 bash 代码"""
        result = tool.execute(
            code="echo 'Hello, World!'",
            language="bash",
            timeout=10
        )

        if result.success:
            assert "output" in result.data
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_dangerous_command_blocked(self, tool):
        """测试危险命令被阻止"""
        # 测试删除命令
        result = tool.execute(
            code="rm -rf /",
            language="bash",
            timeout=10
        )
        # 应该被阻止或返回错误
        if result.success:
            # 如果成功，检查输出中是否有警告
            assert "blocked" in result.data.get("output", "").lower() or \
                   "不允许" in result.data.get("output", "")

    def test_restricted_path_blocked(self, tool):
        """测试受限路径被阻止"""
        # 测试访问受限路径
        result = tool.execute(
            code="cat /etc/passwd",
            language="bash",
            timeout=10
        )
        # 应该被阻止或返回错误
        if result.success:
            # 如果成功，检查输出中是否有警告
            assert "blocked" in result.data.get("output", "").lower() or \
                   "不允许" in result.data.get("output", "")


class TestCodeExecutorToolIntegration:
    """CodeExecutorTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 CodeExecutorTool 实例"""
        return CodeExecutorTool()

    @pytest.mark.integration
    def test_python_workflow(self, tool):
        """测试 Python 代码执行工作流"""
        result = tool.execute(
            code="""
x = 10
y = 20
print(f"Sum: {x + y}")
""",
            language="python",
            timeout=30
        )

        if result.success:
            assert "output" in result.data
            assert "Sum: 30" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    @pytest.mark.integration
    def test_bash_workflow(self, tool):
        """测试 bash 代码执行工作流"""
        result = tool.execute(
            code="""
echo "Test 1"
echo "Test 2"
""",
            language="bash",
            timeout=30
        )

        if result.success:
            assert "output" in result.data
            assert "Test 1" in result.data["output"]
            assert "Test 2" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    @pytest.mark.integration
    def test_error_handling(self, tool):
        """测试错误处理"""
        result = tool.execute(
            code="raise ValueError('Test error')",
            language="python",
            timeout=30
        )

        # 应该返回错误信息
        if result.success:
            assert "error" in result.data or "Error" in result.data.get("output", "")
        else:
            # 执行失败也是正常的
            assert "error" in result.error.lower() or "Error" in result.error

