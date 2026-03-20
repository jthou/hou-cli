"""ContextManager 测试"""
import pytest
import tempfile
from pathlib import Path
from backend.core.context.manager import ContextManager
from backend.core.context.models import MessageRole
from backend.core.context.long_term_memory import FileLongTermMemory, MemoryType


class TestContextManager:
    """ContextManager 测试"""
    
    @pytest.fixture
    def manager(self):
        """创建 ContextManager 实例（使用临时目录）"""
        temp_dir = Path(tempfile.mkdtemp())
        return ContextManager(storage_dir=temp_dir)
    
    def test_create_session(self, manager):
        """测试创建会话"""
        session_id = manager.create_session()
        
        assert session_id is not None
        assert len(session_id) > 0
        
        # 验证会话已创建
        session = manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
    
    def test_add_and_get_messages(self, manager):
        """测试添加和获取消息"""
        session_id = manager.create_session()
        
        manager.add_message(session_id, MessageRole.USER, "你好")
        manager.add_message(session_id, MessageRole.ASSISTANT, "你好！")
        
        messages = manager.get_messages(session_id)
        assert len(messages) == 2
        assert messages[0].content == "你好"
        assert messages[0].role == MessageRole.USER
        assert messages[1].content == "你好！"
        assert messages[1].role == MessageRole.ASSISTANT
    
    def test_get_messages_for_llm(self, manager):
        """测试获取 LLM 格式的消息"""
        session_id = manager.create_session()
        manager.add_message(session_id, MessageRole.USER, "你好")
        
        llm_messages = manager.get_messages_for_llm(session_id)
        
        assert len(llm_messages) == 1
        assert llm_messages[0]["role"] == "user"
        assert llm_messages[0]["content"] == "你好"
    
    def test_compression(self, manager):
        """测试消息压缩"""
        session_id = manager.create_session()
        
        # 添加 15 条消息
        for i in range(15):
            manager.add_message(session_id, MessageRole.USER, f"消息{i}")
        
        # 获取消息（应该压缩到 10 条）
        messages = manager.get_messages(session_id, max_messages=10)
        assert len(messages) == 10
        # 应该保留最近 10 条
        assert messages[0].content == "消息5"
        assert messages[-1].content == "消息14"
    
    def test_search_messages(self, manager):
        """测试搜索消息"""
        session_id = manager.create_session()
        manager.add_message(session_id, MessageRole.USER, "Python 编程")
        manager.add_message(session_id, MessageRole.USER, "Java 开发")
        
        results = manager.search_messages(session_id, "Python")
        
        assert len(results) > 0
        assert any("Python" in msg.content for msg in results)
    
    def test_clear_session(self, manager):
        """测试清除会话"""
        session_id = manager.create_session()
        manager.add_message(session_id, MessageRole.USER, "测试消息")
        
        result = manager.clear_session(session_id)
        assert result is True
        
        messages = manager.get_messages(session_id)
        assert len(messages) == 0
    
    def test_list_sessions(self, manager):
        """测试列出会话"""
        # 创建多个会话
        session_ids = []
        for i in range(3):
            session_id = manager.create_session()
            session_ids.append(session_id)
            manager.add_message(session_id, MessageRole.USER, f"消息{i}")
        
        sessions = manager.list_sessions()
        assert len(sessions) == 3
    
    def test_long_term_memory_integration(self, manager):
        """测试长期记忆集成"""
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        long_term_memory = FileLongTermMemory(storage_dir=temp_dir / "memory")
        
        # 创建带长期记忆的 ContextManager
        memory_manager = ContextManager(
            storage_dir=temp_dir / "contexts",
            long_term_memory=long_term_memory,
            auto_save_to_memory=True
        )
        
        session_id = memory_manager.create_session()
        
        # 添加用户消息（应该自动保存到长期记忆）
        memory_manager.add_message(session_id, MessageRole.USER, "我喜欢使用 Python")
        
        # 验证消息已保存到长期记忆
        memories = long_term_memory.search_memories("Python", top_k=5)
        assert len(memories) > 0
        assert any("Python" in mem.content for mem in memories)
    
    def test_get_relevant_memories(self, manager):
        """测试获取相关记忆"""
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        long_term_memory = FileLongTermMemory(storage_dir=temp_dir / "memory")
        
        # 添加一些记忆
        from backend.core.context.long_term_memory import Memory
        memory = Memory(
            memory_id="mem_1",
            memory_type=MemoryType.KNOWLEDGE,
            content="Python 是一种高级编程语言"
        )
        long_term_memory.save_memory(memory)
        
        # 创建带长期记忆的 ContextManager
        memory_manager = ContextManager(
            storage_dir=temp_dir / "contexts",
            long_term_memory=long_term_memory
        )
        
        # 获取相关记忆
        relevant = memory_manager.get_relevant_memories("Python", top_k=5)
        assert len(relevant) > 0
        assert any("Python" in mem.content for mem in relevant)
    
    def test_manual_save_to_memory(self, manager):
        """测试手动保存到长期记忆"""
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        long_term_memory = FileLongTermMemory(storage_dir=temp_dir / "memory")
        
        memory_manager = ContextManager(
            storage_dir=temp_dir / "contexts",
            long_term_memory=long_term_memory,
            auto_save_to_memory=False  # 不自动保存
        )
        
        session_id = memory_manager.create_session()
        
        # 手动保存到长期记忆
        memory_manager.add_message(
            session_id,
            MessageRole.USER,
            "important information",
            save_to_memory=True
        )
        
        # 验证已保存
        memories = long_term_memory.search_memories("important", top_k=5)
        assert len(memories) > 0
        assert any("important" in mem.content.lower() for mem in memories)

    def test_get_daily_log_context_for_llm(self, manager):
        """测试获取每日日志上下文（短期记忆）"""
        # 写入一条日志
        manager.daily_log_memory.write_daily_entry("今日完成 Python 重构")
        block = manager.get_daily_log_context_for_llm(hours=48)
        assert "今日完成 Python 重构" in block

    def test_get_daily_log_context_empty(self, manager):
        """无每日日志时返回空字符串"""
        block = manager.get_daily_log_context_for_llm(hours=48)
        assert block == ""

