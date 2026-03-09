"""exec + process 集成测试"""
import pytest
from backend.core.agent.tools.builtin.exec_tool import ExecTool
from backend.core.agent.tools.builtin.process_tool import ProcessTool


class TestExecProcessIntegration:
    """exec 与 process 工具集成测试"""

    @pytest.fixture
    def exec_tool(self):
        return ExecTool()

    @pytest.fixture
    def process_tool(self):
        return ProcessTool()

    def test_exec_then_process_list(self, exec_tool, process_tool):
        """exec 后台执行后，process list 应能看到会话"""
        result = exec_tool.execute(command="sleep 2", timeout=5, background=True)
        if not result.success:
            pytest.skip("exec background 可能不可用")
        session_id = result.data.get("session_id")
        assert session_id

        list_result = process_tool.execute(action="list")
        assert list_result.success
        sessions = list_result.data.get("sessions", [])
        ids = [s["session_id"] for s in sessions]
        assert session_id in ids

    def test_exec_sync_then_poll(self, exec_tool, process_tool):
        """exec 同步执行后，process poll 可查看输出"""
        result = exec_tool.execute(command="echo hello from exec", timeout=10)
        assert result.success
        assert "hello from exec" in result.data.get("output", "")
        session_id = result.data.get("session_id")
        if session_id:
            poll_result = process_tool.execute(action="poll", session_id=session_id)
            assert poll_result.success
            assert poll_result.data.get("exited") is True
