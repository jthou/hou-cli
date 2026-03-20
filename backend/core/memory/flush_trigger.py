"""压缩前记忆刷新触发

设计文档：docs/design/01-three-level-memory-and-context-design.md 9.4
当会话接近压缩时，触发静默回合提醒模型写入持久记忆。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.core.context.manager import ContextManager

# 默认阈值：消息数超过此值且未刷新过则触发
DEFAULT_MESSAGE_THRESHOLD = 15
# 软 token 阈值（粗略估算：1 token ≈ 4 字符）
DEFAULT_SOFT_THRESHOLD_TOKENS = 4000


class MemoryFlushTrigger:
    """压缩前记忆刷新触发"""

    def __init__(
        self,
        message_threshold: int = DEFAULT_MESSAGE_THRESHOLD,
        soft_threshold_tokens: int = DEFAULT_SOFT_THRESHOLD_TOKENS,
    ):
        self.message_threshold = message_threshold
        self.soft_threshold_tokens = soft_threshold_tokens

    def should_flush(
        self,
        context_manager: "ContextManager",
        session_id: str,
        message_count: int,
        estimated_tokens: Optional[int] = None,
    ) -> bool:
        """
        是否应触发记忆刷新
        条件：消息数超过阈值 或 估算 token 超过阈值，且本周期未刷新过
        """
        if not getattr(context_manager, "daily_log_memory", None) and not getattr(
            context_manager, "long_term_memory", None
        ):
            return False
        session = context_manager.get_session(session_id)
        if not session:
            return False
        meta = session.metadata or {}
        if meta.get("memory_flush_done"):
            return False
        if message_count >= self.message_threshold:
            return True
        if estimated_tokens is not None and estimated_tokens >= self.soft_threshold_tokens:
            return True
        return False

    def get_flush_prompt(self, recent_context: str = "") -> str:
        """获取刷新提示（注入给 LLM）"""
        return (
            "会话即将压缩，请将本对话中值得持久记忆的内容写入记忆。"
            "使用 memory_write 工具：layer=daily 写每日日志，layer=long 写长期记忆。"
            "若无内容需存储，直接回复 NO_REPLY。"
        )

    def mark_flushed(self, context_manager: "ContextManager", session_id: str) -> bool:
        """标记本周期已刷新"""
        return context_manager.update_session_metadata(session_id, {"memory_flush_done": True})
