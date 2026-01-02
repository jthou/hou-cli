"""Message 和 Session 数据模型测试"""
import pytest
from datetime import datetime
from backend.core.context.models import Message, MessageRole, Session


class TestMessage:
    """Message 数据模型测试"""
    
    def test_message_creation(self):
        """测试创建 Message"""
        message = Message(
            role=MessageRole.USER,
            content="测试消息",
            message_id="msg_123"
        )
        
        assert message.role == MessageRole.USER
        assert message.content == "测试消息"
        assert message.message_id == "msg_123"
        assert isinstance(message.timestamp, datetime)
        assert isinstance(message.metadata, dict)
    
    def test_message_to_dict(self):
        """测试 Message 序列化"""
        message = Message(
            role=MessageRole.USER,
            content="测试消息",
            message_id="msg_123"
        )
        
        data = message.to_dict()
        
        assert data["role"] == "user"
        assert data["content"] == "测试消息"
        assert data["message_id"] == "msg_123"
        assert "timestamp" in data
        assert "metadata" in data
    
    def test_message_from_dict(self):
        """测试 Message 反序列化"""
        data = {
            "role": "user",
            "content": "测试消息",
            "message_id": "msg_123",
            "timestamp": "2025-01-01T12:00:00",
            "metadata": {}
        }
        
        message = Message.from_dict(data)
        
        assert message.role == MessageRole.USER
        assert message.content == "测试消息"
        assert message.message_id == "msg_123"
        assert isinstance(message.timestamp, datetime)
    
    def test_message_role_enum(self):
        """测试 MessageRole 枚举"""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.TOOL.value == "tool"
    
    def test_message_serialization_round_trip(self):
        """测试 Message 序列化往返"""
        original = Message(
            role=MessageRole.ASSISTANT,
            content="回复消息",
            metadata={"key": "value"}
        )
        
        data = original.to_dict()
        restored = Message.from_dict(data)
        
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.metadata == original.metadata


class TestSession:
    """Session 数据模型测试"""
    
    def test_session_creation(self):
        """测试创建 Session"""
        session = Session(
            session_id="session_123",
            metadata={"key": "value"}
        )
        
        assert session.session_id == "session_123"
        assert session.metadata == {"key": "value"}
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
    
    def test_session_to_dict(self):
        """测试 Session 序列化"""
        session = Session(session_id="session_123")
        
        data = session.to_dict()
        
        assert data["session_id"] == "session_123"
        assert "created_at" in data
        assert "updated_at" in data
        assert "metadata" in data
    
    def test_session_from_dict(self):
        """测试 Session 反序列化"""
        data = {
            "session_id": "session_123",
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:00",
            "metadata": {}
        }
        
        session = Session.from_dict(data)
        
        assert session.session_id == "session_123"
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
    
    def test_session_serialization_round_trip(self):
        """测试 Session 序列化往返"""
        original = Session(
            session_id="session_123",
            metadata={"key": "value"}
        )
        
        data = original.to_dict()
        restored = Session.from_dict(data)
        
        assert restored.session_id == original.session_id
        assert restored.metadata == original.metadata

