"""时间窗口压缩策略"""
from typing import List, Optional
from backend.core.context.compression.base import CompressionStrategy
from backend.core.context.models import Message


class TimeWindowCompression(CompressionStrategy):
    """时间窗口压缩（保留最近的消息）"""
    
    def compress(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """压缩消息列表"""
        if max_messages and len(messages) > max_messages:
            return messages[-max_messages:]
        return messages

