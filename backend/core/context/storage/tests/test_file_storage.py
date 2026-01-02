"""FileStorageBackend 测试"""
import pytest
import tempfile
import shutil
from pathlib import Path
from backend.core.context.storage.file import FileStorageBackend
from backend.core.context.models import Message, MessageRole, Session


class TestFileStorageBackend:
    """FileStorageBackend 测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """创建 FileStorageBackend 实例"""
        return FileStorageBackend(storage_dir=temp_dir)
    
    def test_create_session(self, storage):
        """测试创建会话"""
        session = Session(session_id="test_session")
        result = storage.create_session(session)
        
        assert result is True
        retrieved_session = storage.get_session("test_session")
        assert retrieved_session is not None
        assert retrieved_session.session_id == "test_session"
    
    def test_save_message(self, storage):
        """测试保存消息"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        message = Message(
            role=MessageRole.USER,
            content="测试消息"
        )
        
        result = storage.save_message(session_id, message)
        assert result is True
        
        messages = storage.get_messages(session_id)
        assert len(messages) == 1
        assert messages[0].content == "测试消息"
        assert messages[0].role == MessageRole.USER
    
    def test_get_messages_with_limit(self, storage):
        """测试获取消息（带 limit）"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        # 添加 5 条消息
        for i in range(5):
            message = Message(
                role=MessageRole.USER,
                content=f"消息{i}"
            )
            storage.save_message(session_id, message)
        
        # 获取前 3 条
        messages = storage.get_messages(session_id, limit=3)
        assert len(messages) == 3
        assert messages[0].content == "消息0"
        assert messages[2].content == "消息2"
    
    def test_get_messages_with_offset(self, storage):
        """测试获取消息（带 offset）"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        # 添加 5 条消息
        for i in range(5):
            message = Message(
                role=MessageRole.USER,
                content=f"消息{i}"
            )
            storage.save_message(session_id, message)
        
        # 从第 2 条开始获取
        messages = storage.get_messages(session_id, offset=2)
        assert len(messages) == 3
        assert messages[0].content == "消息2"
    
    def test_delete_message(self, storage):
        """测试删除消息"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        message = Message(
            role=MessageRole.USER,
            content="要删除的消息"
        )
        storage.save_message(session_id, message)
        message_id = message.message_id
        
        result = storage.delete_message(session_id, message_id)
        assert result is True
        
        messages = storage.get_messages(session_id)
        assert len(messages) == 0
    
    def test_clear_session(self, storage):
        """测试清除会话"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        # 添加消息
        message = Message(
            role=MessageRole.USER,
            content="测试消息"
        )
        storage.save_message(session_id, message)
        
        # 清除会话
        result = storage.clear_session(session_id)
        assert result is True
        
        # 验证消息已清除
        messages = storage.get_messages(session_id)
        assert len(messages) == 0
        
        # 验证会话已删除
        session = storage.get_session(session_id)
        assert session is None
    
    def test_list_sessions(self, storage):
        """测试列出会话"""
        # 创建多个会话
        for i in range(3):
            session = Session(session_id=f"session_{i}")
            storage.create_session(session)
        
        sessions = storage.list_sessions()
        assert len(sessions) == 3
    
    def test_persistence(self, storage, temp_dir):
        """测试数据持久化"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        message = Message(
            role=MessageRole.USER,
            content="持久化测试"
        )
        storage.save_message(session_id, message)
        
        # 重新创建 storage（模拟重启）
        new_storage = FileStorageBackend(storage_dir=temp_dir)
        messages = new_storage.get_messages(session_id)
        
        assert len(messages) == 1
        assert messages[0].content == "持久化测试"

