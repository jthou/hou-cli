"""检索引擎接口"""
from abc import ABC, abstractmethod
from typing import List
from backend.core.context.models import Message


class RetrievalEngine(ABC):
    """检索引擎接口"""
    
    @abstractmethod
    def search(
        self,
        messages: List[Message],
        query: str,
        top_k: int = 5
    ) -> List[Message]:
        """搜索相关消息"""
        pass

