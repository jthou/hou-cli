"""DatabaseStorageBackend 测试"""
import pytest
import tempfile
import os
from pathlib import Path
from backend.core.context.storage.database import DatabaseStorageBackend
from backend.core.context.models import Message, MessageRole, Session
from datetime import datetime


class TestDatabaseStorageBackend:
    """DatabaseStorageBackend 测试"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库文件"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_path = temp_file.name
        temp_file.close()
        yield temp_path
        # 清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def storage(self, temp_db):
        """创建 DatabaseStorageBackend 实例"""
        return DatabaseStorageBackend(db_path=temp_db)
    
    def test_create_session(self, storage):
        """测试创建会话"""
        session = Session(session_id="test_session")
        result = storage.create_session(session)
        
        assert result is True
        assert storage.get_session("test_session") is not None
        assert storage.get_session("test_session").session_id == "test_session"
    
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
        assert messages[0].message_id is not None
    
    def test_get_messages_with_limit(self, storage):
        """测试获取消息（带 limit）"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        for i in range(5):
            message = Message(
                role=MessageRole.USER,
                content=f"消息{i}"
            )
            storage.save_message(session_id, message)
        
        messages = storage.get_messages(session_id, limit=3)
        assert len(messages) == 3
        assert messages[0].content == "消息0"
        assert messages[2].content == "消息2"
    
    def test_get_messages_with_offset(self, storage):
        """测试获取消息（带 offset）"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        for i in range(5):
            message = Message(
                role=MessageRole.USER,
                content=f"消息{i}"
            )
            storage.save_message(session_id, message)
        
        messages = storage.get_messages(session_id, offset=2, limit=2)
        assert len(messages) == 2
        assert messages[0].content == "消息2"
        assert messages[1].content == "消息3"
    
    def test_delete_message(self, storage):
        """测试删除消息"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        msg1 = Message(role=MessageRole.USER, content="消息1")
        msg2 = Message(role=MessageRole.USER, content="消息2")
        storage.save_message(session_id, msg1)
        storage.save_message(session_id, msg2)
        
        assert len(storage.get_messages(session_id)) == 2
        
        result = storage.delete_message(session_id, msg1.message_id)
        assert result is True
        assert len(storage.get_messages(session_id)) == 1
        assert storage.get_messages(session_id)[0].content == "消息2"
    
    def test_clear_session(self, storage):
        """测试清除会话"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        storage.save_message(session_id, Message(role=MessageRole.USER, content="消息"))
        
        assert len(storage.get_messages(session_id)) == 1
        
        result = storage.clear_session(session_id)
        assert result is True
        assert len(storage.get_messages(session_id)) == 0
        assert storage.get_session(session_id) is None
    
    def test_list_sessions(self, storage):
        """测试列出会话"""
        session1 = Session(session_id="session1")
        session2 = Session(session_id="session2")
        storage.create_session(session1)
        storage.create_session(session2)
        
        sessions = storage.list_sessions()
        assert len(sessions) == 2
        assert {s.session_id for s in sessions} == {"session1", "session2"}
    
    def test_persistence(self, storage, temp_db):
        """测试数据持久化"""
        session_id = "test_session_persistence"
        storage.create_session(Session(session_id=session_id))
        
        message = Message(
            role=MessageRole.USER,
            content="持久化测试"
        )
        storage.save_message(session_id, message)
        
        # 重新创建 storage（模拟重启）
        new_storage = DatabaseStorageBackend(db_path=temp_db)
        messages = new_storage.get_messages(session_id)
        session = new_storage.get_session(session_id)
        
        assert len(messages) == 1
        assert messages[0].content == "持久化测试"
        assert session is not None
        assert session.session_id == session_id
    
    def test_transaction_rollback(self, storage):
        """测试事务回滚"""
        session_id = "test_session"
        storage.create_session(Session(session_id=session_id))
        
        # 正常保存
        message1 = Message(role=MessageRole.USER, content="消息1")
        storage.save_message(session_id, message1)
        
        # 验证已保存
        assert len(storage.get_messages(session_id)) == 1

