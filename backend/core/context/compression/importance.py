"""重要性评分压缩策略"""
from typing import List, Optional, Callable
from backend.core.context.compression.base import CompressionStrategy
from backend.core.context.models import Message, MessageRole


class ImportanceScoringCompression(CompressionStrategy):
    """重要性评分压缩"""
    
    def __init__(self, tokenizer: Optional[Callable[[str], int]] = None):
        """
        初始化重要性评分压缩策略
        
        Args:
            tokenizer: 自定义 tokenizer 函数，默认使用简单估算（1 token ≈ 4 字符）
        """
        self.tokenizer = tokenizer or (lambda text: len(text) // 4)
        self.important_keywords = ["错误", "问题", "重要", "关键", "失败", "异常"]
    
    def _calculate_importance(self, message: Message, all_messages: List[Message]) -> float:
        """计算消息重要性分数"""
        score = 0.0
        
        # 系统消息重要性高
        if message.role == MessageRole.SYSTEM:
            score += 10.0
        
        # 最近的消息重要性高（最近 5 条）
        if message in all_messages[-5:]:
            score += 5.0
        
        # 包含关键词的消息重要性高
        content_lower = message.content.lower()
        for keyword in self.important_keywords:
            if keyword in content_lower:
                score += 2.0
        
        # 用户消息通常比助手消息重要
        if message.role == MessageRole.USER:
            score += 1.0
        
        return score
    
    def compress(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """压缩消息列表"""
        if not messages:
            return []
        
        # 如果只有 max_messages 且消息数在限制内，检查是否需要按时间排序
        if max_messages and len(messages) <= max_messages:
            if not max_tokens:
                # 即使不需要压缩，也返回按时间排序的消息（保持一致性）
                return sorted(messages, key=lambda msg: msg.timestamp)
        
        # 计算每条消息的重要性分数
        scored_messages = [
            (self._calculate_importance(msg, messages), msg)
            for msg in messages
        ]
        
        # 按分数排序（降序）
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        # 选择最重要的消息，直到达到限制
        compressed = []
        tokens_used = 0
        
        for score, msg in scored_messages:
            tokens = self.tokenizer(msg.content)
            
            if max_tokens and tokens_used + tokens > max_tokens:
                continue
            
            if max_messages and len(compressed) >= max_messages:
                break
            
            compressed.append(msg)
            if max_tokens:
                tokens_used += tokens
        
        # 按时间顺序重新排序
        compressed = sorted(compressed, key=lambda msg: msg.timestamp)
        
        return compressed

