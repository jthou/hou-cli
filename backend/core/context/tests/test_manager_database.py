"""ContextManager 与 DatabaseStorageBackend 集成测试"""
import pytest
import tempfile
import os
from pathlib import Path
from backend.core.context.manager import ContextManager
from backend.core.context.storage.database import DatabaseStorageBackend
from backend.core.context.models import MessageRole


class TestContextManagerWithDatabase:
    """ContextManager 与 DatabaseStorageBackend 集成测试"""
    
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
    def manager(self, temp_db):
        """创建使用 DatabaseStorageBackend 的 ContextManager"""
        storage = DatabaseStorageBackend(db_path=temp_db)
        return ContextManager(storage_backend=storage)
    
    def test_create_session(self, manager):
        """测试创建会话"""
        session_id = manager.create_session()
        assert session_id is not None
        
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
        assert messages[1].content == "你好！"
    
    def test_persistence(self, manager, temp_db):
        """测试数据持久化"""
        session_id = manager.create_session()
        manager.add_message(session_id, MessageRole.USER, "持久化测试")
        
        # 重新创建 manager（模拟重启）
        storage = DatabaseStorageBackend(db_path=temp_db)
        new_manager = ContextManager(storage_backend=storage)
        
        messages = new_manager.get_messages(session_id)
        assert len(messages) == 1
        assert messages[0].content == "持久化测试"
    
    def test_storage_backend_switching(self):
        """测试存储后端切换"""
        import tempfile
        from backend.core.context.storage.file import FileStorageBackend
        
        # 使用 FileStorageBackend
        temp_dir = Path(tempfile.mkdtemp())
        file_storage = FileStorageBackend(storage_dir=temp_dir)
        file_manager = ContextManager(storage_backend=file_storage)
        
        session_id = file_manager.create_session()
        file_manager.add_message(session_id, MessageRole.USER, "文件存储")
        
        # 切换到 DatabaseStorageBackend
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db = temp_file.name
        temp_file.close()
        
        db_storage = DatabaseStorageBackend(db_path=temp_db)
        db_manager = ContextManager(storage_backend=db_storage)
        
        session_id2 = db_manager.create_session()
        db_manager.add_message(session_id2, MessageRole.USER, "数据库存储")
        
        # 验证两个存储后端都正常工作
        assert len(file_manager.get_messages(session_id)) == 1
        assert len(db_manager.get_messages(session_id2)) == 1
        
        # 清理
        if os.path.exists(temp_db):
            os.unlink(temp_db)

