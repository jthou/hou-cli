"""压缩策略接口"""
from abc import ABC, abstractmethod
from typing import List, Optional
from backend.core.context.models import Message


class CompressionStrategy(ABC):
    """压缩策略接口"""
    
    @abstractmethod
    def compress(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """压缩消息列表"""
        pass

