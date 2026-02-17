"""ContextManager 测试"""
import pytest
from backend.core.agent.context_manager import ContextManager


class TestContextManager:
    """ContextManager 测试类"""
    
    @pytest.fixture
    def context_manager(self):
        """创建 ContextManager 实例"""
        return ContextManager(max_history=10)
    
    def test_create_session(self, context_manager):
        """测试创建会话"""
        session_id = context_manager.create_session()
        assert session_id is not None
        assert len(session_id) > 0
        assert session_id in context_manager.sessions
    
    def test_add_message(self, context_manager):
        """测试添加消息"""
        session_id = context_manager.create_session()
        context_manager.add_message(session_id, "user", "你好")
        
        history = context_manager.get_history(session_id)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "你好"
    
    def test_get_history(self, context_manager):
        """测试获取历史"""
        session_id = context_manager.create_session()
        context_manager.add_message(session_id, "user", "消息1")
        context_manager.add_message(session_id, "assistant", "回复1")
        
        history = context_manager.get_history(session_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
    
    def test_max_history_limit(self, context_manager):
        """测试历史消息数量限制"""
        session_id = context_manager.create_session()
        
        # 添加超过限制的消息
        for i in range(15):
            context_manager.add_message(session_id, "user", f"消息{i}")
        
        history = context_manager.get_history(session_id)
        # 应该只保留最近 10 条
        assert len(history) == 10
        assert history[0]["content"] == "消息5"  # 最早的是第5条
        assert history[-1]["content"] == "消息14"  # 最新的是第14条
    
    def test_clear_session(self, context_manager):
        """测试清除会话"""
        session_id = context_manager.create_session()
        context_manager.add_message(session_id, "user", "消息1")
        
        context_manager.clear_session(session_id)
        history = context_manager.get_history(session_id)
        assert len(history) == 0
    
    def test_auto_create_session(self, context_manager):
        """测试自动创建会话"""
        # 使用不存在的 session_id 添加消息
        session_id = "new_session_123"
        context_manager.add_message(session_id, "user", "消息1")
        
        # 应该自动创建会话
        assert session_id in context_manager.sessions
        history = context_manager.get_history(session_id)
        assert len(history) == 1
    
    def test_get_history_for_llm(self, context_manager):
        """测试获取 LLM 格式的历史"""
        session_id = context_manager.create_session()
        context_manager.add_message(session_id, "user", "消息1")
        context_manager.add_message(session_id, "assistant", "回复1")
        
        llm_history = context_manager.get_history_for_llm(session_id)
        assert len(llm_history) == 2
        assert llm_history[0]["role"] == "user"
        assert llm_history[1]["role"] == "assistant"
















