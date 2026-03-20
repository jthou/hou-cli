"""LegacyMemoryAdapter - 适配现有长期记忆接口到新记忆系统

设计文档：docs/design/01-three-level-memory-and-context-design.md 7.3
过渡期维持对 ContextManager.get_relevant_memories() 的兼容。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from backend.core.context.long_term_memory.models import Memory, MemoryType

if TYPE_CHECKING:
    from backend.core.context.manager import ContextManager


class LegacyMemoryAdapter:
    """适配现有长期记忆接口到新记忆系统"""

    def __init__(self, context_manager: "ContextManager"):
        """
        Args:
            context_manager: ContextManager，含 long_term_memory
        """
        self.context_manager = context_manager

    def search(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 10
    ) -> List[Memory]:
        """委托给 context_manager.get_relevant_memories"""
        return self.context_manager.get_relevant_memories(
            query, memory_type=memory_type, top_k=top_k
        )
