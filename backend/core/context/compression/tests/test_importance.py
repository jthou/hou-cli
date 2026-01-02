"""ImportanceScoringCompression 测试"""
import pytest
from datetime import datetime, timedelta
from backend.core.context.compression.importance import ImportanceScoringCompression
from backend.core.context.models import Message, MessageRole


class TestImportanceScoringCompression:
    """ImportanceScoringCompression 测试"""
    
    @pytest.fixture
    def compression(self):
        """创建 ImportanceScoringCompression 实例"""
        return ImportanceScoringCompression()
    
    def test_system_message_high_score(self, compression):
        """测试系统消息获得高分"""
        messages = [
            Message(role=MessageRole.USER, content="普通消息"),
            Message(role=MessageRole.SYSTEM, content="系统消息"),
            Message(role=MessageRole.ASSISTANT, content="助手消息")
        ]
        
        score = compression._calculate_importance(messages[1], messages)
        assert score >= 10.0  # 系统消息至少 +10.0
    
    def test_recent_messages_high_score(self, compression):
        """测试最近 5 条消息获得加分"""
        base_time = datetime.now()
        messages = [
            Message(role=MessageRole.USER, content=f"消息{i}", timestamp=base_time + timedelta(seconds=i))
            for i in range(10)
        ]
        
        # 最后 5 条消息应该获得 +5.0
        for i in range(5, 10):
            score = compression._calculate_importance(messages[i], messages)
            assert score >= 5.0
    
    def test_keyword_matching(self, compression):
        """测试关键词匹配加分"""
        messages = [
            Message(role=MessageRole.USER, content="普通消息"),
            Message(role=MessageRole.USER, content="这是一个错误"),
            Message(role=MessageRole.USER, content="重要的问题"),
            Message(role=MessageRole.USER, content="关键信息")
        ]
        
        # 包含关键词的消息应该获得 +2.0
        score_error = compression._calculate_importance(messages[1], messages)
        score_important = compression._calculate_importance(messages[2], messages)
        score_key = compression._calculate_importance(messages[3], messages)
        
        assert score_error >= 2.0
        assert score_important >= 2.0
        assert score_key >= 2.0
    
    def test_user_message_bonus(self, compression):
        """测试用户消息获得加分"""
        messages = [
            Message(role=MessageRole.USER, content="用户消息"),
            Message(role=MessageRole.ASSISTANT, content="助手消息")
        ]
        
        user_score = compression._calculate_importance(messages[0], messages)
        assistant_score = compression._calculate_importance(messages[1], messages)
        
        # 用户消息应该比助手消息分数高（至少 +1.0）
        assert user_score > assistant_score
    
    def test_compress_by_importance(self, compression):
        """测试按重要性压缩"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="系统消息"),
            Message(role=MessageRole.USER, content="普通消息1"),
            Message(role=MessageRole.USER, content="普通消息2"),
            Message(role=MessageRole.USER, content="普通消息3"),
            Message(role=MessageRole.USER, content="重要的问题"),  # 包含关键词
        ]
        
        # 限制 2 条消息，应该保留系统消息和包含关键词的消息
        result = compression.compress(messages, max_messages=2)
        assert len(result) == 2
        assert any(msg.role == MessageRole.SYSTEM for msg in result)
        assert any("问题" in msg.content for msg in result)
    
    def test_compress_preserves_time_order(self, compression):
        """测试压缩后保持时间顺序"""
        base_time = datetime.now()
        messages = [
            Message(role=MessageRole.USER, content="消息1", timestamp=base_time),
            Message(role=MessageRole.SYSTEM, content="系统", timestamp=base_time + timedelta(seconds=0.5)),
            Message(role=MessageRole.USER, content="消息2", timestamp=base_time + timedelta(seconds=1)),
            Message(role=MessageRole.USER, content="重要", timestamp=base_time + timedelta(seconds=1.5)),
        ]
        
        result = compression.compress(messages, max_messages=3)
        
        # 验证时间顺序
        timestamps = [msg.timestamp for msg in result]
        assert timestamps == sorted(timestamps)
    
    def test_compress_with_token_limit(self, compression):
        """测试带 token 限制的压缩"""
        # 创建长消息
        messages = [
            Message(role=MessageRole.SYSTEM, content="系统消息"),
            Message(role=MessageRole.USER, content="x" * 100),  # 25 tokens
            Message(role=MessageRole.USER, content="重要的问题" + "x" * 50),  # 包含关键词
            Message(role=MessageRole.USER, content="y" * 100),  # 25 tokens
        ]
        
        # 限制 30 tokens，应该保留系统消息和包含关键词的消息
        result = compression.compress(messages, max_tokens=30)
        total_tokens = sum(len(msg.content) // 4 for msg in result)
        assert total_tokens <= 30
        assert any(msg.role == MessageRole.SYSTEM for msg in result)
    
    def test_empty_messages(self, compression):
        """测试空消息列表"""
        result = compression.compress([], max_messages=5)
        assert len(result) == 0
    
    def test_no_compression_when_under_limit(self, compression):
        """测试当消息数在限制内时不压缩"""
        messages = [
            Message(role=MessageRole.USER, content="消息1"),
            Message(role=MessageRole.USER, content="消息2")
        ]
        
        result = compression.compress(messages, max_messages=5)
        assert len(result) == 2
        assert result == sorted(messages, key=lambda msg: msg.timestamp)
    
    def test_combined_scoring(self, compression):
        """测试组合评分（系统消息 + 最近 + 关键词）"""
        base_time = datetime.now()
        messages = [
            Message(role=MessageRole.USER, content="普通消息1", timestamp=base_time),
            Message(role=MessageRole.USER, content="普通消息2", timestamp=base_time + timedelta(seconds=1)),
            Message(role=MessageRole.USER, content="普通消息3", timestamp=base_time + timedelta(seconds=2)),
            Message(role=MessageRole.USER, content="普通消息4", timestamp=base_time + timedelta(seconds=3)),
            Message(role=MessageRole.SYSTEM, content="系统消息重要", timestamp=base_time + timedelta(seconds=4)),  # 系统 + 最近 + 关键词
        ]
        
        # 系统消息应该获得最高分（系统 +10.0，最近 +5.0，关键词 +2.0 = 17.0）
        system_score = compression._calculate_importance(messages[4], messages)
        assert system_score >= 17.0

