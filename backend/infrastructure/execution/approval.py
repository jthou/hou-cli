"""审批管理器

借鉴 OpenClaw：管理待审批请求，签发 approval_token，校验 token 有效性。
"""
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# 配置
APPROVAL_TIMEOUT_SEC = int(os.getenv("EXEC_APPROVAL_TIMEOUT_SEC", "120"))


@dataclass
class PendingApproval:
    """待审批请求"""
    id: str
    command: str
    workdir: str
    language: str
    risk_level: str
    reason: str
    created_at: float
    expires_at: float
    code: str = ""  # execute_code 的 code 字段
    tool_name: str = "execute_code"  # execute_code | exec


class ApprovalManager:
    """审批管理器

    内存存储，支持 create/approve/reject/verify_token。
    """

    def __init__(self, timeout_sec: int = APPROVAL_TIMEOUT_SEC):
        self.timeout_sec = timeout_sec
        self._pending: Dict[str, PendingApproval] = {}
        self._tokens: Dict[str, PendingApproval] = {}  # token -> pending（一次性消费）

    def create_pending(
        self,
        command: str,
        workdir: str,
        language: str,
        risk_level: str,
        reason: str,
        code: str = "",
        tool_name: str = "execute_code"
    ) -> PendingApproval:
        """创建待审批请求"""
        now = time.time()
        approval_id = f"ap_{uuid.uuid4().hex[:12]}"
        pending = PendingApproval(
            id=approval_id,
            command=command,
            workdir=workdir,
            language=language,
            risk_level=risk_level,
            reason=reason,
            created_at=now,
            expires_at=now + self.timeout_sec,
            code=code,
            tool_name=tool_name
        )
        self._pending[approval_id] = pending
        return pending

    def approve(self, approval_id: str, user_id: Optional[str] = None) -> str:
        """
        审批通过，返回 approval_token。

        Args:
            approval_id: 待审批 ID
            user_id: 可选用户 ID

        Returns:
            approval_token，用于后续执行时携带

        Raises:
            ValueError: approval_id 不存在或已过期
        """
        pending = self._pending.get(approval_id)
        if not pending:
            raise ValueError(f"审批请求不存在或已失效: {approval_id}")
        if time.time() > pending.expires_at:
            del self._pending[approval_id]
            raise ValueError(f"审批请求已过期: {approval_id}")

        token = secrets.token_urlsafe(32)
        self._tokens[token] = pending
        del self._pending[approval_id]
        return token

    def approve_with_info(self, approval_id: str) -> Dict[str, Any]:
        """
        审批通过并返回 token 与待执行信息，供 approve-execution API 使用。

        Returns:
            dict: approval_token, tool_name, code, language, command
        """
        pending = self._pending.get(approval_id)
        if not pending:
            raise ValueError(f"审批请求不存在或已失效: {approval_id}")
        if time.time() > pending.expires_at:
            del self._pending[approval_id]
            raise ValueError(f"审批请求已过期: {approval_id}")

        token = secrets.token_urlsafe(32)
        self._tokens[token] = pending
        del self._pending[approval_id]
        return {
            "approval_token": token,
            "tool_name": pending.tool_name,
            "code": pending.code,
            "language": pending.language,
            "command": pending.command,
            "workdir": pending.workdir or ".",
        }

    def reject(self, approval_id: str) -> None:
        """拒绝审批"""
        if approval_id in self._pending:
            del self._pending[approval_id]

    def verify_token(self, token: str) -> Optional[PendingApproval]:
        """
        校验 token 并消费（一次性）。

        Returns:
            PendingApproval 若有效，否则 None
        """
        pending = self._tokens.pop(token, None)
        if not pending:
            return None
        if time.time() > pending.expires_at:
            return None
        return pending


# 单例
_default_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """获取默认 ApprovalManager 实例"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ApprovalManager()
    return _default_manager
