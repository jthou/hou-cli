"""Memory 数据模型测试"""
import pytest
from datetime import datetime
from backend.core.context.long_term_memory.models import Memory, MemoryType


class TestMemoryType:
    """MemoryType 枚举测试"""
    
    def test_memory_type_enum(self):
        """测试 MemoryType 枚举值"""
        assert MemoryType.CONVERSATION.value == "conversation"
        assert MemoryType.KNOWLEDGE.value == "knowledge"
        assert MemoryType.PREFERENCE.value == "preference"
        assert MemoryType.CODE.value == "code"
        assert MemoryType.TASK.value == "task"


class TestMemory:
    """Memory 数据模型测试"""
    
    def test_memory_creation(self):
        """测试创建 Memory"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.CONVERSATION,
            content="测试记忆内容",
            summary="测试摘要",
            tags=["tag1", "tag2"]
        )
        
        assert memory.memory_id == "mem_123"
        assert memory.memory_type == MemoryType.CONVERSATION
        assert memory.content == "测试记忆内容"
        assert memory.summary == "测试摘要"
        assert memory.tags == ["tag1", "tag2"]
        assert isinstance(memory.created_at, datetime)
        assert isinstance(memory.updated_at, datetime)
        assert memory.access_count == 0
        assert memory.last_accessed is None
    
    def test_memory_to_dict(self):
        """测试 Memory 序列化"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.KNOWLEDGE,
            content="知识内容",
            summary="知识摘要"
        )
        
        data = memory.to_dict()
        
        assert data["memory_id"] == "mem_123"
        assert data["memory_type"] == "knowledge"
        assert data["content"] == "知识内容"
        assert data["summary"] == "知识摘要"
        assert "created_at" in data
        assert "updated_at" in data
        assert "access_count" in data
        assert data["access_count"] == 0
    
    def test_memory_from_dict(self):
        """测试 Memory 反序列化"""
        data = {
            "memory_id": "mem_123",
            "memory_type": "conversation",
            "content": "测试内容",
            "summary": "测试摘要",
            "tags": ["tag1"],
            "metadata": {},
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:00",
            "access_count": 5,
            "last_accessed": "2025-01-01T13:00:00"
        }
        
        memory = Memory.from_dict(data)
        
        assert memory.memory_id == "mem_123"
        assert memory.memory_type == MemoryType.CONVERSATION
        assert memory.content == "测试内容"
        assert memory.access_count == 5
        assert isinstance(memory.last_accessed, datetime)
    
    def test_memory_serialization_round_trip(self):
        """测试 Memory 序列化往返"""
        original = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.CODE,
            content="代码片段",
            summary="代码摘要",
            tags=["python", "code"],
            metadata={"key": "value"}
        )
        
        data = original.to_dict()
        restored = Memory.from_dict(data)
        
        assert restored.memory_id == original.memory_id
        assert restored.memory_type == original.memory_type
        assert restored.content == original.content
        assert restored.tags == original.tags
        assert restored.metadata == original.metadata
    
    def test_memory_default_values(self):
        """测试 Memory 默认值"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.CONVERSATION,
            content="内容"
        )
        
        assert memory.summary is None
        assert memory.tags == []
        assert memory.metadata == {}
        assert memory.access_count == 0
        assert memory.last_accessed is None

