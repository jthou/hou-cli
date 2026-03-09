"""ProcessTool 测试"""
import pytest
from backend.core.agent.tools.builtin.process_tool import ProcessTool


class TestProcessTool:
    """ProcessTool 测试"""

    @pytest.fixture
    def tool(self):
        return ProcessTool()

    def test_tool_initialization(self, tool):
        """工具初始化"""
        assert tool.name == "process"
        assert "action" in [p.name for p in tool.parameters]

    def test_list_empty(self, tool):
        """list 无会话时返回空"""
        result = tool.execute(action="list")
        assert result.success is True
        assert "sessions" in result.data
        assert isinstance(result.data["sessions"], list)

    def test_poll_nonexistent(self, tool):
        """poll 不存在的 session 应失败"""
        result = tool.execute(action="poll", session_id="ps_nonexistent")
        assert result.success is False
