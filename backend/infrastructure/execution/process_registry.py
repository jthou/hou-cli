"""进程注册表

借鉴 OpenClaw：管理 exec 启动的后台进程。
"""
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# 配置
SESSION_TTL_MINUTES = int(os.getenv("PROCESS_SESSION_TTL_MINUTES", "30"))
TAIL_MAX_CHARS = 4096


@dataclass
class ProcessSession:
    """进程会话"""
    id: str
    command: str
    pid: Optional[int]
    cwd: str
    started_at: float
    aggregated: str = ""
    tail: str = ""
    exited: bool = False
    exit_code: Optional[int] = None
    backgrounded: bool = False


class ProcessRegistry:
    """进程注册表

    管理 exec 启动的进程，支持输出聚合、LRU 清理。
    """

    def __init__(self, ttl_minutes: int = SESSION_TTL_MINUTES):
        self.ttl_seconds = ttl_minutes * 60
        self._sessions: Dict[str, ProcessSession] = {}

    def add(self, session: ProcessSession) -> None:
        """添加会话"""
        self._sessions[session.id] = session

    def get(self, session_id: str) -> Optional[ProcessSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def list_running(self, scope_key: Optional[str] = None) -> List[ProcessSession]:
        """列出运行中的会话（未退出且未 backgrounded 或 backgrounded 的）"""
        now = time.time()
        result = []
        for s in self._sessions.values():
            if s.exited:
                if now - s.started_at > self.ttl_seconds:
                    continue  # 已超时，跳过
            result.append(s)
        return result

    def mark_backgrounded(self, session_id: str) -> None:
        """标记为后台"""
        s = self._sessions.get(session_id)
        if s:
            s.backgrounded = True

    def append_output(self, session_id: str, stdout: str, stderr: str) -> None:
        """追加输出"""
        s = self._sessions.get(session_id)
        if not s:
            return
        if stdout:
            s.aggregated += stdout
        if stderr:
            s.aggregated += stderr
        s.tail = s.aggregated[-TAIL_MAX_CHARS:] if len(s.aggregated) > TAIL_MAX_CHARS else s.aggregated

    def tail_output(self, session_id: str, max_chars: int = TAIL_MAX_CHARS) -> str:
        """获取尾部输出"""
        s = self._sessions.get(session_id)
        if not s:
            return ""
        if len(s.aggregated) <= max_chars:
            return s.aggregated
        return s.aggregated[-max_chars:]

    def mark_exited(self, session_id: str, exit_code: int) -> None:
        """标记已退出"""
        s = self._sessions.get(session_id)
        if s:
            s.exited = True
            s.exit_code = exit_code

    def remove(self, session_id: str) -> bool:
        """移除会话（仅限已退出）"""
        s = self._sessions.get(session_id)
        if s and s.exited:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """清理过期会话，返回清理数量"""
        now = time.time()
        to_remove = [
            sid for sid, s in self._sessions.items()
            if s.exited and (now - s.started_at) > self.ttl_seconds
        ]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    @staticmethod
    def create_session_id() -> str:
        """生成会话 ID"""
        return f"ps_{uuid.uuid4().hex[:12]}"


# 单例
_default_registry: Optional[ProcessRegistry] = None


def get_process_registry() -> ProcessRegistry:
    """获取默认 ProcessRegistry 实例"""
    global _default_registry
    if _default_registry is None:
        _default_registry = ProcessRegistry()
    return _default_registry
