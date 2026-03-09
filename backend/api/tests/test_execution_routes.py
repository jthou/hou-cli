"""执行审批 API 测试"""
import pytest
from backend.infrastructure.execution.approval import get_approval_manager


def test_approve_success(client):
    """审批成功应返回 token"""
    manager = get_approval_manager()
    pending = manager.create_pending(
        command="rm -rf ./build",
        workdir="",
        language="zsh",
        risk_level="medium",
        reason="删除操作"
    )
    response = client.post(
        "/api/execution/approve",
        json={"approval_id": pending.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert "approval_token" in data
    assert data["approval_id"] == pending.id


def test_approve_nonexistent(client):
    """审批不存在的 ID 应返回 400"""
    response = client.post(
        "/api/execution/approve",
        json={"approval_id": "ap_nonexistent"}
    )
    assert response.status_code == 400


def test_reject(client):
    """拒绝审批应成功"""
    manager = get_approval_manager()
    pending = manager.create_pending(
        command="ls",
        workdir="",
        language="zsh",
        risk_level="low",
        reason=""
    )
    response = client.post(
        "/api/execution/reject",
        json={"approval_id": pending.id}
    )
    assert response.status_code == 200
    assert response.json().get("status") == "rejected"
