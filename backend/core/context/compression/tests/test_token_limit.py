"""TokenLimitCompression 测试"""
import pytest
from backend.core.context.compression.token_limit import TokenLimitCompression
from backend.core.context.models import Message, MessageRole


class TestTokenLimitCompression:
    """TokenLimitCompression 测试"""
    
    @pytest.fixture
    def compression(self):
        """创建 TokenLimitCompression 实例"""
        return TokenLimitCompression()
    
    def test_default_tokenizer(self, compression):
        """测试默认 tokenizer"""
        # 1 token ≈ 4 字符
        assert compression._default_tokenizer("") == 0
        assert compression._default_tokenizer("test") == 1  # 4 字符 = 1 token
        assert compression._default_tokenizer("test test") == 2  # 9 字符 = 2 token
        assert compression._default_tokenizer("x" * 20) == 5  # 20 字符 = 5 tokens
    
    def test_custom_tokenizer(self):
        """测试自定义 tokenizer"""
        def custom_tokenizer(text: str) -> int:
            return len(text) // 2  # 1 token = 2 字符
        
        compression = TokenLimitCompression(tokenizer=custom_tokenizer)
        assert compression.tokenizer("test") == 2  # 4 字符 = 2 tokens
    
    def test_no_compression_when_under_limit(self, compression):
        """测试当消息数在限制内时不压缩"""
        messages = [
            Message(role=MessageRole.USER, content="消息1"),
            Message(role=MessageRole.USER, content="消息2")
        ]
        
        result = compression.compress(messages, max_tokens=100)
        assert len(result) == 2
        assert result == messages
    
    def test_compress_when_over_token_limit(self, compression):
        """测试当超过 token 限制时压缩"""
        # 创建 5 条消息，每条 20 字符 = 5 tokens，总共 25 tokens
        messages = [
            Message(role=MessageRole.USER, content="x" * 20),
            Message(role=MessageRole.USER, content="x" * 20),
            Message(role=MessageRole.USER, content="x" * 20),
            Message(role=MessageRole.USER, content="x" * 20),
            Message(role=MessageRole.USER, content="x" * 20)
        ]
        
        # 限制 10 tokens，应该只保留最后 2 条（从后往前）
        result = compression.compress(messages, max_tokens=10)
        assert len(result) == 2
        assert result[0].content == messages[3].content
        assert result[1].content == messages[4].content
    
    def test_system_messages_priority(self, compression):
        """测试系统消息优先保留"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="系统消息"),
            Message(role=MessageRole.USER, content="x" * 20),
            Message(role=MessageRole.USER, content="x" * 20),
            Message(role=MessageRole.USER, content="x" * 20)
        ]
        
        # 限制 5 tokens，应该保留系统消息和最后一条用户消息
        result = compression.compress(messages, max_tokens=5)
        assert len(result) >= 1
        # 系统消息应该被保留
        assert any(msg.role == MessageRole.SYSTEM for msg in result)
    
    def test_only_max_messages(self, compression):
        """测试只有 max_messages 限制"""
        messages = [
            Message(role=MessageRole.USER, content=f"消息{i}")
            for i in range(10)
        ]
        
        result = compression.compress(messages, max_messages=5)
        assert len(result) == 5
        # 应该保留最后 5 条
        assert result[0].content == "消息5"
        assert result[-1].content == "消息9"
    
    def test_empty_messages(self, compression):
        """测试空消息列表"""
        result = compression.compress([], max_tokens=10)
        assert len(result) == 0
    
    def test_single_message(self, compression):
        """测试单条消息"""
        messages = [Message(role=MessageRole.USER, content="单条消息")]
        result = compression.compress(messages, max_tokens=10)
        assert len(result) == 1
        assert result[0].content == "单条消息"
    
    def test_preserve_time_order(self, compression):
        """测试保留时间顺序"""
        from datetime import datetime, timedelta
        
        base_time = datetime.now()
        messages = [
            Message(role=MessageRole.USER, content="消息1", timestamp=base_time),
            Message(role=MessageRole.USER, content="消息2", timestamp=base_time + timedelta(seconds=1)),
            Message(role=MessageRole.USER, content="消息3", timestamp=base_time + timedelta(seconds=2)),
            Message(role=MessageRole.SYSTEM, content="系统", timestamp=base_time + timedelta(seconds=0.5))
        ]
        
        result = compression.compress(messages, max_tokens=20)
        # 验证时间顺序
        timestamps = [msg.timestamp for msg in result]
        assert timestamps == sorted(timestamps)

