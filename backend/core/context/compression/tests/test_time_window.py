"""TimeWindowCompression 测试"""
import pytest
from backend.core.context.compression.time_window import TimeWindowCompression
from backend.core.context.models import Message, MessageRole


class TestTimeWindowCompression:
    """TimeWindowCompression 测试"""
    
    @pytest.fixture
    def compression(self):
        """创建 TimeWindowCompression 实例"""
        return TimeWindowCompression()
    
    def test_no_compression_when_under_limit(self, compression):
        """测试消息数未超过限制时不压缩"""
        messages = [
            Message(role=MessageRole.USER, content=f"消息{i}")
            for i in range(5)
        ]
        
        result = compression.compress(messages, max_messages=10)
        
        assert len(result) == 5
        assert result == messages
    
    def test_compress_when_over_limit(self, compression):
        """测试消息数超过限制时压缩"""
        messages = [
            Message(role=MessageRole.USER, content=f"消息{i}")
            for i in range(15)
        ]
        
        result = compression.compress(messages, max_messages=10)
        
        assert len(result) == 10
        # 应该保留最近 10 条
        assert result[0].content == "消息5"
        assert result[-1].content == "消息14"
    
    def test_empty_messages(self, compression):
        """测试空消息列表"""
        result = compression.compress([], max_messages=10)
        assert len(result) == 0
    
    def test_no_max_messages_limit(self, compression):
        """测试没有 max_messages 限制时返回全部消息"""
        messages = [
            Message(role=MessageRole.USER, content=f"消息{i}")
            for i in range(5)
        ]
        
        result = compression.compress(messages, max_messages=None)
        assert len(result) == 5
        assert result == messages

