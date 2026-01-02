"""压缩策略性能基准测试"""
import pytest
import time
from datetime import datetime, timedelta
from backend.core.context.compression.time_window import TimeWindowCompression
from backend.core.context.compression.token_limit import TokenLimitCompression
from backend.core.context.compression.importance import ImportanceScoringCompression
from backend.core.context.models import Message, MessageRole


class TestCompressionPerformance:
    """压缩策略性能测试"""
    
    def _generate_messages(self, count: int) -> list[Message]:
        """生成测试消息"""
        base_time = datetime.now()
        messages = []
        for i in range(count):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            content = f"消息 {i}: " + "x" * 100  # 每条消息约 25 tokens
            messages.append(Message(
                role=role,
                content=content,
                timestamp=base_time + timedelta(seconds=i)
            ))
        return messages
    
    def test_time_window_performance(self):
        """测试 TimeWindowCompression 性能"""
        compression = TimeWindowCompression()
        
        for count in [100, 1000, 10000]:
            messages = self._generate_messages(count)
            
            start_time = time.time()
            result = compression.compress(messages, max_messages=50)
            elapsed = time.time() - start_time
            
            assert len(result) == 50
            assert elapsed < 1.0  # 应该在 1 秒内完成
            print(f"TimeWindowCompression ({count} messages): {elapsed:.4f}s")
    
    def test_token_limit_performance(self):
        """测试 TokenLimitCompression 性能"""
        compression = TokenLimitCompression()
        
        for count in [100, 1000, 10000]:
            messages = self._generate_messages(count)
            
            start_time = time.time()
            result = compression.compress(messages, max_tokens=1000)
            elapsed = time.time() - start_time
            
            assert elapsed < 2.0  # 应该在 2 秒内完成
            print(f"TokenLimitCompression ({count} messages): {elapsed:.4f}s")
    
    def test_importance_performance(self):
        """测试 ImportanceScoringCompression 性能"""
        compression = ImportanceScoringCompression()
        
        for count in [100, 1000, 10000]:
            messages = self._generate_messages(count)
            
            start_time = time.time()
            result = compression.compress(messages, max_messages=50)
            elapsed = time.time() - start_time
            
            assert elapsed < 5.0  # 应该在 5 秒内完成（计算分数需要时间）
            print(f"ImportanceScoringCompression ({count} messages): {elapsed:.4f}s")
    
    def test_compression_effectiveness(self):
        """测试压缩效果"""
        messages = self._generate_messages(100)
        
        # TimeWindowCompression
        tw_compression = TimeWindowCompression()
        tw_result = tw_compression.compress(messages, max_messages=10)
        assert len(tw_result) == 10
        
        # TokenLimitCompression
        tl_compression = TokenLimitCompression()
        tl_result = tl_compression.compress(messages, max_tokens=250)
        assert len(tl_result) <= 10  # 约 10 条消息 = 250 tokens
        
        # ImportanceScoringCompression
        imp_compression = ImportanceScoringCompression()
        imp_result = imp_compression.compress(messages, max_messages=10)
        assert len(imp_result) == 10
        
        print(f"TimeWindow: {len(tw_result)} messages")
        print(f"TokenLimit: {len(tl_result)} messages")
        print(f"Importance: {len(imp_result)} messages")
    
    def test_important_messages_preserved(self):
        """测试重要消息是否被保留"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="系统消息"),
            Message(role=MessageRole.USER, content="普通消息1"),
            Message(role=MessageRole.USER, content="普通消息2"),
            Message(role=MessageRole.USER, content="重要的问题"),  # 包含关键词
            Message(role=MessageRole.USER, content="普通消息3"),
        ]
        
        # ImportanceScoringCompression 应该保留系统消息和包含关键词的消息
        compression = ImportanceScoringCompression()
        result = compression.compress(messages, max_messages=2)
        
        assert len(result) == 2
        assert any(msg.role == MessageRole.SYSTEM for msg in result)
        assert any("问题" in msg.content for msg in result)
    
    def test_compression_quality(self):
        """测试压缩质量（重要信息保留率）"""
        # 创建包含重要消息的列表
        messages = []
        important_count = 0
        
        for i in range(100):
            if i % 10 == 0:
                # 每 10 条消息中有一条重要消息
                messages.append(Message(
                    role=MessageRole.USER,
                    content=f"重要的问题 {i}",
                    timestamp=datetime.now() + timedelta(seconds=i)
                ))
                important_count += 1
            else:
                messages.append(Message(
                    role=MessageRole.USER,
                    content=f"普通消息 {i}",
                    timestamp=datetime.now() + timedelta(seconds=i)
                ))
        
        # 使用 ImportanceScoringCompression 压缩
        compression = ImportanceScoringCompression()
        result = compression.compress(messages, max_messages=20)
        
        # 计算重要消息保留率
        important_preserved = sum(1 for msg in result if "问题" in msg.content)
        retention_rate = important_preserved / important_count if important_count > 0 else 0
        
        print(f"重要消息保留率: {retention_rate:.2%}")
        assert retention_rate > 0.5  # 至少保留 50% 的重要消息

