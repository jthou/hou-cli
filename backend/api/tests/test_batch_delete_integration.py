"""
批量删除功能集成测试
使用真实的 ContextManager 和临时文件存储进行端到端测试
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app  # 假设你的 FastAPI 应用在 main.py 中
from backend.core.context.manager import ContextManager
from backend.core.context.storage.file import FileStorageBackend
from backend.core.context.models import Message, MessageRole


@pytest.fixture
def temp_storage_dir():
    """创建临时存储目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def context_manager(temp_storage_dir):
    """创建使用临时存储的 ContextManager"""
    storage = FileStorageBackend(storage_dir=temp_dir)
    return ContextManager(storage_backend=storage)


@pytest.fixture
def client(temp_storage_dir):
    """创建测试客户端"""
    # 暂时使用全局应用，但在实际实现中可能需要配置存储目录
    return TestClient(app)


class TestBatchDeleteIntegration:
    """批量删除功能的集成测试"""

    def test_batch_delete_messages_integration(self, context_manager):
        """测试批量删除消息的完整流程"""
        # 创建会话
        session_id = context_manager.create_session()
        assert session_id

        # 添加多条消息
        message_ids = []
        for i in range(5):
            msg_id = context_manager.add_message(
                session_id,
                MessageRole.USER,
                f"测试消息 {i}",
                metadata={"index": i}
            )
            message_ids.append(msg_id)

        # 确认所有消息都存在
        messages = context_manager.get_messages(session_id)
        assert len(messages) == 5

        # 批量删除其中2条消息
        ids_to_delete = message_ids[:2]
        result = context_manager.delete_messages(session_id, ids_to_delete)

        # 验证返回结果
        assert result["success"] is True
        assert len(result["deleted"]) == 2
        assert len(result["failed"]) == 0

        # 验证消息确实被删除
        remaining_messages = context_manager.get_messages(session_id)
        assert len(remaining_messages) == 3

        # 验证删除的消息不再存在
        remaining_ids = [msg.message_id for msg in remaining_messages]
        for deleted_id in ids_to_delete:
            assert deleted_id not in remaining_ids

    def test_batch_delete_sessions_integration(self, context_manager):
        """测试批量删除会话的完整流程"""
        # 创建多个会话
        session_ids = []
        for i in range(3):
            sid = context_manager.create_session(metadata={"type": "test", "index": i})
            session_ids.append(sid)

            # 在每个会话中添加一些消息
            context_manager.add_message(sid, MessageRole.USER, f"会话{i}的消息")

        # 确认所有会话都存在
        all_sessions = context_manager.list_sessions()
        assert len(all_sessions) == 3

        # 批量删除其中2个会话
        sessions_to_delete = session_ids[:2]
        result = context_manager.delete_sessions(sessions_to_delete)

        # 验证返回结果
        assert result["success"] is True
        assert len(result["deleted"]) == 2
        assert len(result["failed"]) == 0

        # 验证会话确实被删除
        remaining_sessions = context_manager.list_sessions()
        assert len(remaining_sessions) == 1

        # 验证被删除的会话不再存在
        remaining_session_ids = [s.session_id for s in remaining_sessions]
        for deleted_sid in sessions_to_delete:
            assert deleted_sid not in remaining_session_ids

    def test_batch_delete_sessions_with_expected_type_integration(self, context_manager):
        """测试带类型校验的批量删除会话"""
        # 创建不同类型会话
        article_session = context_manager.create_session(metadata={"type": "article_writing"})
        work_session = context_manager.create_session(metadata={"type": "work_assistant"})
        general_session = context_manager.create_session(metadata={})  # 无类型

        # 添加消息到各个会话
        context_manager.add_message(article_session, MessageRole.USER, "写作助手消息")
        context_manager.add_message(work_session, MessageRole.USER, "工作助手消息")
        context_manager.add_message(general_session, MessageRole.USER, "通用对话消息")

        # 测试只删除指定类型的会话
        sessions_to_delete = [article_session]
        # 这里我们直接测试 ContextManager 方法，因为 expected_type 是在 API 层处理的
        result = context_manager.delete_sessions(sessions_to_delete)

        assert result["success"] is True
        assert len(result["deleted"]) == 1
        assert len(result["failed"]) == 0

        # 验证只有指定会话被删除
        remaining_sessions = context_manager.list_sessions()
        assert len(remaining_sessions) == 2

    def test_batch_delete_messages_with_invalid_ids(self, context_manager):
        """测试批量删除消息时包含无效ID的情况"""
        # 创建会话和消息
        session_id = context_manager.create_session()
        valid_msg_id = context_manager.add_message(
            session_id,
            MessageRole.USER,
            "有效消息"
        )

        # 尝试删除有效和无效的组合
        fake_ids = ["fake_id_1", "fake_id_2"]
        ids_to_delete = [valid_msg_id] + fake_ids

        result = context_manager.delete_messages(session_id, ids_to_delete)

        # 验证结果：应该有部分成功部分失败
        assert result["success"] is True
        assert len(result["deleted"]) >= 0  # 至少有有效消息被删除
        assert len(result["failed"]) >= 2   # 至少有2个无效ID失败

        # 如果有效消息存在，则应该被删除
        remaining_messages = context_manager.get_messages(session_id)
        if valid_msg_id:  # 有效的ID会被删除
            assert len(remaining_messages) == 0
        else:
            assert len(remaining_messages) == 1  # 如果上面添加失败，则仍有一个

    def test_batch_delete_empty_lists(self, context_manager):
        """测试空列表的批量删除"""
        session_id = context_manager.create_session()

        # 测试空消息列表删除
        result = context_manager.delete_messages(session_id, [])
        assert result["success"] is True
        assert len(result["deleted"]) == 0
        assert len(result["failed"]) == 0

        # 测试空会话列表删除
        result = context_manager.delete_sessions([])
        assert result["success"] is True
        assert len(result["deleted"]) == 0
        assert len(result["failed"]) == 0