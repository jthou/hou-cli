"""长期记忆接口"""
from abc import ABC, abstractmethod
from typing import List, Optional
from backend.core.context.long_term_memory.models import Memory, MemoryType


class LongTermMemory(ABC):
    """长期记忆接口"""
    
    @abstractmethod
    def save_memory(self, memory: Memory) -> bool:
        """保存记忆"""
        pass
    
    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        pass
    
    @abstractmethod
    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 10
    ) -> List[Memory]:
        """搜索记忆"""
        pass
    
    @abstractmethod
    def get_memories_by_tags(
        self,
        tags: List[str],
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """根据标签获取记忆"""
        pass
    
    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def update_memory(self, memory: Memory) -> bool:
        """更新记忆"""
        pass

