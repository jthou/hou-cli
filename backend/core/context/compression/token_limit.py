"""Token 限制压缩策略"""
from typing import List, Optional, Callable
from backend.core.context.compression.base import CompressionStrategy
from backend.core.context.models import Message, MessageRole


class TokenLimitCompression(CompressionStrategy):
    """Token 限制压缩"""
    
    def __init__(self, tokenizer: Optional[Callable[[str], int]] = None):
        """
        初始化 Token 限制压缩策略
        
        Args:
            tokenizer: 自定义 tokenizer 函数，默认使用简单估算（1 token ≈ 4 字符）
        """
        self.tokenizer = tokenizer or self._default_tokenizer
    
    def _default_tokenizer(self, text: str) -> int:
        """默认 tokenizer（简单估算：1 token ≈ 4 字符）"""
        return len(text) // 4
    
    def compress(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """压缩消息列表"""
        if not messages:
            return []
        
        # 如果只有 max_messages，使用时间窗口压缩
        if not max_tokens:
            if max_messages and len(messages) > max_messages:
                return messages[-max_messages:]
            return messages
        
        # 计算总 token 数
        total_tokens = sum(self.tokenizer(msg.content) for msg in messages)
        
        if total_tokens <= max_tokens:
            # 如果总 token 数在限制内，但需要检查 max_messages
            if max_messages and len(messages) > max_messages:
                # 按时间排序后保留最后 max_messages 条
                sorted_messages = sorted(messages, key=lambda msg: msg.timestamp)
                return sorted_messages[-max_messages:]
            # 即使不需要压缩，也返回按时间排序的消息（保持一致性）
            return sorted(messages, key=lambda msg: msg.timestamp)
        
        # 策略：优先保留系统消息，然后从后往前保留其他消息
        system_messages_selected = []
        other_messages_selected = []
        tokens_used = 0
        
        # 1. 优先保留系统消息
        system_messages = [msg for msg in messages if msg.role == MessageRole.SYSTEM]
        for msg in system_messages:
            tokens = self.tokenizer(msg.content)
            if tokens_used + tokens <= max_tokens:
                system_messages_selected.append(msg)
                tokens_used += tokens
        
        # 2. 从后往前保留其他消息
        other_messages = [msg for msg in messages if msg.role != MessageRole.SYSTEM]
        for msg in reversed(other_messages):
            tokens = self.tokenizer(msg.content)
            if tokens_used + tokens <= max_tokens:
                other_messages_selected.append(msg)
                tokens_used += tokens
            else:
                break
        
        # 反转 other_messages_selected 以保持时间顺序（因为是从后往前添加的）
        other_messages_selected.reverse()
        
        # 3. 合并消息（系统消息 + 其他消息）
        compressed = system_messages_selected + other_messages_selected
        
        # 4. 按时间顺序重新排序（必须排序，因为系统消息和其他消息的时间戳可能交错）
        compressed = sorted(compressed, key=lambda msg: msg.timestamp)
        
        # 5. 如果还有 max_messages 限制，进一步限制（保留最后 max_messages 条）
        if max_messages and len(compressed) > max_messages:
            compressed = compressed[-max_messages:]
            # 限制后需要重新排序（因为取了最后几条，可能顺序不对）
            compressed = sorted(compressed, key=lambda msg: msg.timestamp)
        
        return compressed

