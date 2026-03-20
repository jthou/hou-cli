"""记忆写入工具 - 供 LLM 将重要信息写入短期/长期记忆

设计文档：docs/design/01-three-level-memory-and-context-design.md 2.4
"""
from typing import Any, Optional

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter


class MemoryWriteTool(Tool):
    """将内容写入短期（每日日志）或长期（MEMORY.md）记忆"""

    def __init__(self, context_manager: Any):
        """
        Args:
            context_manager: ContextManager，含 daily_log_memory 和 long_term_memory
        """
        super().__init__(
            name="memory_write",
            description="将重要信息写入记忆。layer=daily 写入每日日志（短期）；layer=long 写入长期记忆（MEMORY.md）。scope=user 用户级跨会话；scope=session 会话级。用户说「记住」或对话中有持久价值的信息时使用。",
            parameters=[
                ToolParameter(name="content", type="string", description="要记住的内容", required=True),
                ToolParameter(
                    name="layer",
                    type="string",
                    description="写入层级：daily=短期每日日志，long=长期记忆",
                    required=False,
                    default="daily",
                    enum=["daily", "long"],
                ),
                ToolParameter(
                    name="scope",
                    type="string",
                    description="长期记忆范围：user=用户级跨会话，session=会话级",
                    required=False,
                    default="user",
                    enum=["user", "session"],
                ),
            ],
        )
        self.context_manager = context_manager

    def execute(self, **kwargs) -> ToolResult:
        content = kwargs.get("content", "").strip()
        layer = kwargs.get("layer", "daily")
        scope = kwargs.get("scope", "user")
        session_id = kwargs.get("session_id", "")
        if not content:
            return ToolResult(success=False, error="content 不能为空")
        if layer not in ("daily", "long"):
            return ToolResult(success=False, error="layer 须为 daily 或 long")

        try:
            if layer == "daily":
                if not getattr(self.context_manager, "daily_log_memory", None):
                    return ToolResult(success=False, error="短期记忆未启用")
                ok = self.context_manager.daily_log_memory.write_daily_entry(content)
                if ok:
                    return ToolResult(success=True, data={"message": "已写入每日日志"})
                return ToolResult(success=False, error="写入每日日志失败")
            else:
                lt = getattr(self.context_manager, "long_term_memory", None)
                if not lt:
                    return ToolResult(success=False, error="长期记忆未启用")
                from backend.core.context.long_term_memory.models import Memory, MemoryType
                meta = {}
                if scope == "session" and session_id:
                    meta["session_id"] = session_id
                mem = Memory(memory_id="", memory_type=MemoryType.CONVERSATION, content=content, metadata=meta)
                ok = lt.save_memory(mem)
                if ok:
                    return ToolResult(success=True, data={"message": "已写入长期记忆"})
                return ToolResult(success=False, error="写入长期记忆失败")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
