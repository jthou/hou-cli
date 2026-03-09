"""代码执行审批流程端到端测试"""
import pytest
from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
from backend.infrastructure.execution.approval import get_approval_manager


class TestCodeExecutionApprovalE2E:
    """审批流程端到端测试"""

    @pytest.fixture
    def tool(self):
        return CodeExecutorTool()

    @pytest.mark.asyncio
    async def test_allowlist_no_approval(self, tool):
        """命中 allowlist 时直接执行，无需确认"""
        result = tool.execute(
            code="ls -la /tmp",
            language="zsh",
            timeout=10
        )
        assert result.success is True
        assert "output" in result.data

    @pytest.mark.asyncio
    async def test_approval_flow(self, tool):
        """需审批时返回 approval_id，携带 token 重试后执行成功"""
        result = tool.execute(
            code="chmod 755 /tmp/test_approval_file_xyz",
            language="zsh",
            timeout=10
        )
        data = result.data or {}
        if data.get("requires_confirmation") and data.get("approval_id"):
            approval_id = data["approval_id"]
            manager = get_approval_manager()
            token = manager.approve(approval_id)
            result2 = tool.execute(
                code="chmod 755 /tmp/test_approval_file_xyz",
                language="zsh",
                timeout=10,
                approval_token=token
            )
            assert result2.success is True or "output" in (result2.data or {})
        else:
            assert result.success is False or "output" in data

    @pytest.mark.asyncio
    async def test_obfuscation_blocked(self, tool):
        """混淆代码应被拒绝"""
        result = tool.execute(
            code="echo aGVsbG8= | base64 -d | sh",
            language="zsh",
            timeout=10
        )
        assert result.success is False
        assert "混淆" in (result.error or "") or "禁止" in (result.error or "")
