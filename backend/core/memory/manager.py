"""MemoryManager - 统一记忆编排层

设计文档：docs/design/01-three-level-memory-and-context-design.md 5
编排短期、近端、长期三层记忆，提供统一入口。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple
from backend.core.memory.models import MemoryLayer, MemoryResult
from backend.core.memory.flush_trigger import MemoryFlushTrigger

logger = logging.getLogger(__name__)


class MemoryManager:
    """统一记忆管理：编排短期、近端、长期三层记忆"""

    def __init__(
        self,
        context_manager: "ContextManager",
        flush_trigger: Optional[MemoryFlushTrigger] = None,
    ):
        """
        Args:
            context_manager: ContextManager，含 daily_log_memory、long_term_memory
            flush_trigger: 压缩前刷新触发，None 时自动创建
        """
        self.context_manager = context_manager
        self.flush_trigger = flush_trigger or MemoryFlushTrigger()

    def get_context_for_llm(
        self,
        session_id: str,
        query: Optional[str] = None,
        include_layers: Tuple[MemoryLayer, ...] = (MemoryLayer.SHORT, MemoryLayer.LONG),
        short_term_hours: int = 48,
        long_term_top_k: int = 5,
    ) -> str:
        """
        聚合三层记忆，返回注入 LLM 的上下文文本
        SESSION 层由 ContextManager.get_messages 单独提供，此处不包含
        """
        parts = []
        if MemoryLayer.SHORT in include_layers and self.context_manager.daily_log_memory:
            short_ctx = self.context_manager.get_daily_log_context_for_llm(hours=short_term_hours)
            if short_ctx:
                parts.append(f"【近期记忆（每日日志）】\n{short_ctx}")
        if MemoryLayer.LONG in include_layers and self.context_manager.long_term_memory:
            lt = self.context_manager.long_term_memory
            if hasattr(lt, "get_content_for_llm"):
                lt_ctx = lt.get_content_for_llm(
                    query=query, top_k=long_term_top_k, session_id=session_id
                )
            elif hasattr(lt, "search_memories") and query:
                memories = lt.search_memories(
                    query, top_k=long_term_top_k, session_id=session_id
                )
                lt_ctx = "\n\n".join(m.content for m in memories)
            else:
                lt_ctx = ""
            if lt_ctx:
                parts.append(f"【长期记忆】\n{lt_ctx}")
        return "\n\n".join(parts) if parts else ""

    def write(
        self,
        content: str,
        layer: MemoryLayer,
        source: str = "system",
        session_id: Optional[str] = None,
    ) -> bool:
        """写入指定层级"""
        if layer == MemoryLayer.SHORT and self.context_manager.daily_log_memory:
            return self.context_manager.daily_log_memory.write_daily_entry(content)
        if layer == MemoryLayer.LONG and self.context_manager.long_term_memory:
            from backend.core.context.long_term_memory.models import Memory, MemoryType
            mem = Memory(memory_id="", memory_type=MemoryType.CONVERSATION, content=content)
            return self.context_manager.long_term_memory.save_memory(mem)
        if layer == MemoryLayer.SESSION:
            logger.warning("MemoryManager.write SESSION 层由 ContextManager.add_message 处理")
            return False
        return False

    def should_flush(
        self,
        session_id: str,
        message_count: int,
        estimated_tokens: Optional[int] = None,
    ) -> bool:
        """是否应触发压缩前刷新"""
        return self.flush_trigger.should_flush(
            self.context_manager, session_id, message_count, estimated_tokens
        )

    def mark_flushed(self, session_id: str) -> bool:
        """标记本周期已刷新"""
        return self.flush_trigger.mark_flushed(self.context_manager, session_id)

    def get_flush_prompt(self, recent_context: str = "") -> str:
        """获取刷新提示"""
        return self.flush_trigger.get_flush_prompt(recent_context)

    def search(
        self,
        query: str,
        layers: Optional[Tuple[MemoryLayer, ...]] = None,
        top_k: int = 10,
        timeout: float = 30.0,
        callback_on_error: Optional[Callable[[Exception], None]] = None,
    ) -> List[MemoryResult]:
        """
        跨层检索
        超时或异常时调用 callback_on_error
        """
        layers = layers or (MemoryLayer.SHORT, MemoryLayer.LONG)
        results: List[MemoryResult] = []
        try:
            if MemoryLayer.LONG in layers and self.context_manager.long_term_memory:
                memories = self.context_manager.long_term_memory.search_memories(
                    query, top_k=top_k
                )
                for m in memories:
                    results.append(MemoryResult(
                        content=m.content,
                        layer=MemoryLayer.LONG,
                        source_id=m.memory_id,
                    ))
            if MemoryLayer.SHORT in layers and self.context_manager.daily_log_memory:
                entries = self.context_manager.daily_log_memory.get_recent_entries(hours=48)
                if entries and query.lower() in entries.lower():
                    results.append(MemoryResult(
                        content=entries[:500] + ("..." if len(entries) > 500 else ""),
                        layer=MemoryLayer.SHORT,
                    ))
        except Exception as e:
            logger.warning("MemoryManager.search 失败: %s", e)
            if callback_on_error:
                callback_on_error(e)
        return results[:top_k]

    def delete(self, layer: MemoryLayer, id_or_path: str) -> bool:
        """按层删除"""
        if layer == MemoryLayer.LONG and self.context_manager.long_term_memory:
            return self.context_manager.long_term_memory.delete_memory(id_or_path)
        if layer == MemoryLayer.SHORT:
            logger.warning("MemoryManager.delete SHORT 层按日期文件管理，暂不支持按 id 删除")
            return False
        if layer == MemoryLayer.SESSION:
            logger.warning("MemoryManager.delete SESSION 层由 ContextManager 管理")
            return False
        return False


if TYPE_CHECKING:
    from backend.core.context.manager import ContextManager
