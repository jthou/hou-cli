"""FileLongTermMemory 测试"""
import pytest
import tempfile
import shutil
from pathlib import Path
from backend.core.context.long_term_memory.file import FileLongTermMemory
from backend.core.context.long_term_memory.models import Memory, MemoryType


class TestFileLongTermMemory:
    """FileLongTermMemory 测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def memory_store(self, temp_dir):
        """创建 FileLongTermMemory 实例"""
        return FileLongTermMemory(storage_dir=temp_dir)
    
    def test_save_memory(self, memory_store, temp_dir):
        """测试保存记忆"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.CONVERSATION,
            content="测试记忆内容"
        )
        
        result = memory_store.save_memory(memory)
        assert result is True
        
        # 验证文件已创建
        memory_file = temp_dir / "memories" / "mem_123.json"
        assert memory_file.exists()
    
    def test_get_memory(self, memory_store):
        """测试获取记忆"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.KNOWLEDGE,
            content="知识内容"
        )
        memory_store.save_memory(memory)
        
        retrieved = memory_store.get_memory("mem_123")
        
        assert retrieved is not None
        assert retrieved.memory_id == "mem_123"
        assert retrieved.content == "知识内容"
        assert retrieved.memory_type == MemoryType.KNOWLEDGE
    
    def test_get_memory_updates_access_count(self, memory_store):
        """测试获取记忆时更新访问计数"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.CONVERSATION,
            content="内容"
        )
        memory_store.save_memory(memory)
        
        # 第一次获取
        retrieved1 = memory_store.get_memory("mem_123")
        assert retrieved1.access_count == 1
        assert retrieved1.last_accessed is not None
        
        # 第二次获取
        retrieved2 = memory_store.get_memory("mem_123")
        assert retrieved2.access_count == 2
    
    def test_search_memories(self, memory_store):
        """测试搜索记忆"""
        # 创建多个记忆
        memory1 = Memory(
            memory_id="mem_1",
            memory_type=MemoryType.CONVERSATION,
            content="Python 编程语言",
            summary="Python 是一种高级编程语言"
        )
        memory2 = Memory(
            memory_id="mem_2",
            memory_type=MemoryType.KNOWLEDGE,
            content="Java 开发",
            tags=["java", "programming"]
        )
        memory3 = Memory(
            memory_id="mem_3",
            memory_type=MemoryType.CONVERSATION,
            content="其他内容"
        )
        
        memory_store.save_memory(memory1)
        memory_store.save_memory(memory2)
        memory_store.save_memory(memory3)
        
        # 搜索 "Python"
        results = memory_store.search_memories("Python", top_k=5)
        
        assert len(results) > 0
        assert any("Python" in mem.content for mem in results)
        # Python 应该排在前面（因为 content 匹配权重更高）
        assert results[0].memory_id == "mem_1"
    
    def test_search_memories_with_type_filter(self, memory_store):
        """测试按类型过滤搜索"""
        memory1 = Memory(
            memory_id="mem_1",
            memory_type=MemoryType.CONVERSATION,
            content="conversation content"
        )
        memory2 = Memory(
            memory_id="mem_2",
            memory_type=MemoryType.KNOWLEDGE,
            content="knowledge content"
        )
        
        memory_store.save_memory(memory1)
        memory_store.save_memory(memory2)
        
        # 只搜索 CONVERSATION 类型
        results = memory_store.search_memories(
            "conversation",
            memory_type=MemoryType.CONVERSATION,
            top_k=10
        )
        
        assert len(results) == 1
        assert results[0].memory_type == MemoryType.CONVERSATION
        assert results[0].memory_id == "mem_1"
    
    def test_get_memories_by_tags(self, memory_store):
        """测试根据标签获取记忆"""
        memory1 = Memory(
            memory_id="mem_1",
            memory_type=MemoryType.CODE,
            content="代码片段1",
            tags=["python", "code"]
        )
        memory2 = Memory(
            memory_id="mem_2",
            memory_type=MemoryType.CODE,
            content="代码片段2",
            tags=["java", "code"]
        )
        memory3 = Memory(
            memory_id="mem_3",
            memory_type=MemoryType.KNOWLEDGE,
            content="知识内容",
            tags=["knowledge"]
        )
        
        memory_store.save_memory(memory1)
        memory_store.save_memory(memory2)
        memory_store.save_memory(memory3)
        
        # 根据标签 "python" 搜索
        results = memory_store.get_memories_by_tags(["python"])
        
        assert len(results) == 1
        assert results[0].memory_id == "mem_1"
        
        # 根据标签 "code" 搜索（应该找到两个）
        results = memory_store.get_memories_by_tags(["code"])
        assert len(results) == 2
    
    def test_delete_memory(self, memory_store):
        """测试删除记忆"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.CONVERSATION,
            content="要删除的内容"
        )
        memory_store.save_memory(memory)
        
        result = memory_store.delete_memory("mem_123")
        assert result is True
        
        # 验证记忆已删除
        retrieved = memory_store.get_memory("mem_123")
        assert retrieved is None
    
    def test_update_memory(self, memory_store):
        """测试更新记忆"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.CONVERSATION,
            content="原始内容"
        )
        memory_store.save_memory(memory)
        
        # 更新内容
        memory.content = "更新后的内容"
        result = memory_store.update_memory(memory)
        assert result is True
        
        # 验证更新
        retrieved = memory_store.get_memory("mem_123")
        assert retrieved.content == "更新后的内容"
        assert retrieved.updated_at > memory.created_at
    
    def test_persistence(self, memory_store, temp_dir):
        """测试数据持久化"""
        memory = Memory(
            memory_id="mem_123",
            memory_type=MemoryType.CONVERSATION,
            content="持久化测试"
        )
        memory_store.save_memory(memory)
        
        # 重新创建 memory_store（模拟重启）
        new_memory_store = FileLongTermMemory(storage_dir=temp_dir)
        retrieved = new_memory_store.get_memory("mem_123")
        
        assert retrieved is not None
        assert retrieved.content == "持久化测试"

