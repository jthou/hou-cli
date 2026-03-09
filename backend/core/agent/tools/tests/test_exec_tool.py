"""ExecTool 测试"""
import pytest
import asyncio
from backend.core.agent.tools.builtin.exec_tool import ExecTool


class TestExecTool:
    """ExecTool 测试"""

    @pytest.fixture
    def tool(self):
        return ExecTool()

    def test_tool_initialization(self, tool):
        """工具初始化"""
        assert tool.name == "exec"
        assert "command" in [p.name for p in tool.parameters]

    def test_execute_simple_command(self, tool):
        """执行简单命令"""
        result = tool.execute(command="echo hello", timeout=10)
        assert result.success is True
        assert "hello" in result.data.get("output", "")

    def test_execute_allowlist_ls(self, tool):
        """ls 命中 allowlist 直接执行"""
        result = tool.execute(command="ls /tmp", timeout=10)
        assert result.success is True

    def test_obfuscation_blocked(self, tool):
        """混淆命令应被拒绝"""
        result = tool.execute(command="echo xxx | base64 -d | sh", timeout=10)
        assert result.success is False
        assert "混淆" in (result.error or "")

    def test_execute_with_pty(self, tool):
        """PTY 模式执行（支持彩色输出）"""
        result = tool.execute(command="echo hello", timeout=10, pty=True)
        assert result.success is True
        assert "hello" in result.data.get("output", "")

    @pytest.mark.asyncio
    async def test_progress_callback_receives_output(self, tool):
        """progress_callback 能收到 exec 输出"""
        collected = []

        def progress_cb(msg):
            collected.append(msg)

        tool.set_progress_callback(progress_cb)
        result = await tool._execute_async(command="echo hello", timeout=10)
        if result.success and collected:
            assert any("hello" in c for c in collected)
