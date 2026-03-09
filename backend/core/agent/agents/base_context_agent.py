"""
专用 Agent 基类：工作助手、通用对话、代码助手等 context_type 驱动的 Agent 共用接口。

各 Agent 通过 stream_process(task, context, delegate) 执行，delegate 提供
_select_model、_chat_with_tools_stream 等编排能力。
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional


class BaseContextAgent(ABC):
    """专用 Agent 基类，与通用对话、工作助手、代码助手并列。"""

    AGENT_ID: str = ""

    def __init__(
        self,
        tool_registry: Any,
        llm_service: Any,
        context_manager: Any,
    ):
        self.tool_registry = tool_registry
        self.llm_service = llm_service
        self.context_manager = context_manager

    @abstractmethod
    async def stream_process(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        delegate: Any,
    ) -> AsyncIterator[str]:
        """流式处理任务，delegate 为 orchestrator，提供 _select_model、_chat_with_tools_stream 等。"""
        pass
