"""审批管理器测试"""
import pytest
import time
from backend.infrastructure.execution.approval import (
    ApprovalManager,
    PendingApproval,
    get_approval_manager,
)


class TestApprovalManager:
    """ApprovalManager 测试"""

    @pytest.fixture
    def manager(self):
        return ApprovalManager(timeout_sec=60)

    def test_create_and_approve(self, manager):
        """create → approve 应返回有效 token"""
        pending = manager.create_pending(
            command="rm -rf ./build",
            workdir="/tmp",
            language="zsh",
            risk_level="medium",
            reason="删除操作"
        )
        assert pending.id.startswith("ap_")
        token = manager.approve(pending.id)
        assert token
        verified = manager.verify_token(token)
        assert verified is not None
        assert verified.command == "rm -rf ./build"

    def test_create_and_reject(self, manager):
        """create → reject 后 verify 应返回 None"""
        pending = manager.create_pending(
            command="rm -rf ./x",
            workdir="",
            language="zsh",
            risk_level="medium",
            reason="删除"
        )
        manager.reject(pending.id)
        with pytest.raises(ValueError):
            manager.approve(pending.id)

    def test_verify_consumes_token(self, manager):
        """approve → verify 两次，第二次应返回 None（token 已消费）"""
        pending = manager.create_pending(
            command="ls",
            workdir="",
            language="zsh",
            risk_level="low",
            reason=""
        )
        token = manager.approve(pending.id)
        first = manager.verify_token(token)
        assert first is not None
        second = manager.verify_token(token)
        assert second is None

    def test_wrong_token(self, manager):
        """无效 token 应返回 None"""
        assert manager.verify_token("invalid-token") is None

    def test_approve_nonexistent(self, manager):
        """审批不存在的 ID 应 raise ValueError"""
        with pytest.raises(ValueError):
            manager.approve("ap_nonexistent")

    def test_expired_approval(self):
        """过期后 approve 应失败"""
        m = ApprovalManager(timeout_sec=1)
        pending = m.create_pending(
            command="ls",
            workdir="",
            language="zsh",
            risk_level="low",
            reason=""
        )
        time.sleep(1.5)
        with pytest.raises(ValueError):
            m.approve(pending.id)
