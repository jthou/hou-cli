"""会话管理路由单元测试"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient
from backend.core.context.models import Session, Message, MessageRole
from backend.core.context.manager import ContextManager


class TestSessionRoutes:
    """会话管理路由测试类"""
    
    @pytest.fixture
    def mock_session(self):
        """创建模拟会话"""
        return Session(
            session_id="test_session_1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"key": "value"}
        )
    
    @pytest.fixture
    def mock_messages(self):
        """创建模拟消息列表"""
        return [
            Message(
                message_id="msg_1",
                role=MessageRole.USER,
                content="用户消息",
                timestamp=datetime.now()
            ),
            Message(
                message_id="msg_2",
                role=MessageRole.ASSISTANT,
                content="助手回复",
                timestamp=datetime.now()
            )
        ]
    
    def test_list_sessions_success(self, client, mock_session):
        """测试列出会话成功"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.list_sessions = MagicMock(return_value=[mock_session])
            mock_orch.context_manager.get_session_preview = MagicMock(return_value={
                "session_id": mock_session.session_id,
                "preview": "测试预览",
                "message_count": 5,
                "created_at": mock_session.created_at.isoformat(),
                "updated_at": mock_session.updated_at.isoformat(),
                "metadata": mock_session.metadata
            })
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/sessions/list?limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert "sessions" in data
            assert len(data["sessions"]) == 1
            assert data["sessions"][0]["session_id"] == mock_session.session_id
    
    def test_list_sessions_with_limit(self, client, mock_session):
        """测试带 limit 参数的列出会话"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.list_sessions = MagicMock(return_value=[mock_session])
            mock_orch.context_manager.get_session_preview = MagicMock(return_value={
                "session_id": mock_session.session_id,
                "preview": "测试预览",
                "message_count": 5,
                "created_at": mock_session.created_at.isoformat(),
                "updated_at": mock_session.updated_at.isoformat(),
                "metadata": mock_session.metadata
            })
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/sessions/list?limit=5")
            
            assert response.status_code == 200
            mock_orch.context_manager.list_sessions.assert_called_once_with(
                limit=5, sort="updated_at", order="desc", offset=0
            )
    
    def test_get_session_detail_success(self, client, mock_session, mock_messages):
        """测试获取会话详情成功"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.get_session = MagicMock(return_value=mock_session)
            mock_orch.context_manager.get_messages = MagicMock(return_value=mock_messages)
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/sessions/test_session_1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["session"]["session_id"] == mock_session.session_id
            assert len(data["messages"]) == 2
    
    def test_get_session_detail_not_found(self, client):
        """测试获取不存在的会话详情"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.get_session = MagicMock(return_value=None)
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/sessions/nonexistent_session")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "不存在" in data["error"]
    
    def test_delete_session_success(self, client):
        """测试删除会话成功（路由调用 delete_session，非 clear_session）"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.delete_session = MagicMock(return_value=True)
            mock_get_orch.return_value = mock_orch
            
            response = client.delete("/api/sessions/test_session_1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_orch.context_manager.delete_session.assert_called_once_with("test_session_1")
    
    def test_delete_session_not_found(self, client):
        """测试删除不存在的会话"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.delete_session = MagicMock(return_value=False)
            mock_get_orch.return_value = mock_orch
            
            response = client.delete("/api/sessions/nonexistent_session")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
    
    def test_delete_message_success(self, client):
        """测试删除单条消息成功"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.delete_message = MagicMock(return_value=True)
            mock_get_orch.return_value = mock_orch

            response = client.delete("/api/sessions/test_session_1/messages/msg_123")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_orch.context_manager.delete_message.assert_called_once_with("test_session_1", "msg_123")

    def test_delete_message_not_found(self, client):
        """测试删除不存在的消息"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.delete_message = MagicMock(return_value=False)
            mock_get_orch.return_value = mock_orch

            response = client.delete("/api/sessions/test_session_1/messages/nonexistent_msg")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_delete_message_integration_real_storage(self, app):
        """集成测试：使用真实存储验证删除接口（2025-03-20）"""
        temp_path = Path(tempfile.mkdtemp())
        try:
            ctx = ContextManager(storage_dir=temp_path)
            session_id = ctx.create_session()
            mid1 = ctx.add_message(session_id, MessageRole.USER, "问题1")
            mid2 = ctx.add_message(session_id, MessageRole.ASSISTANT, "回复1")
            assert len(ctx.get_messages(session_id, compressed=False)) == 2

            with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
                mock_orch = MagicMock()
                mock_orch.context_manager = ctx
                mock_get_orch.return_value = mock_orch

                client = TestClient(app)
                response = client.delete(
                    f"/api/sessions/{session_id}/messages/{mid1}"
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True, data.get("error", "")

            msgs = ctx.get_messages(session_id, compressed=False)
            assert len(msgs) == 1
            assert msgs[0].message_id == mid2
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

    def test_batch_delete_messages_integration_real_storage(self, app):
        """集成测试：真实存储批量删消息（2026-03-21）"""
        temp_path = Path(tempfile.mkdtemp())
        try:
            ctx = ContextManager(storage_dir=temp_path)
            session_id = ctx.create_session()
            m1 = ctx.add_message(session_id, MessageRole.USER, "a")
            m2 = ctx.add_message(session_id, MessageRole.USER, "b")
            m3 = ctx.add_message(session_id, MessageRole.ASSISTANT, "c")
            assert len(ctx.get_messages(session_id, compressed=False)) == 3

            with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
                mock_orch = MagicMock()
                mock_orch.context_manager = ctx
                mock_get_orch.return_value = mock_orch
                client = TestClient(app)
                response = client.post(
                    f"/api/sessions/{session_id}/messages/batch-delete",
                    json={"message_ids": [m1, m2, "nonexistent"]},
                )
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True
            assert set(data.get("deleted", [])) == {m1, m2}
            assert len(data.get("failed", [])) == 1

            msgs = ctx.get_messages(session_id, compressed=False)
            assert len(msgs) == 1
            assert msgs[0].message_id == m3
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

    def test_batch_delete_sessions_integration_real_storage(self, app):
        """集成测试：真实存储批量删会话（2026-03-21）"""
        temp_path = Path(tempfile.mkdtemp())
        try:
            ctx = ContextManager(storage_dir=temp_path)
            sid1 = ctx.create_session(metadata={"type": "work_assistant"})
            sid2 = ctx.create_session(metadata={"type": "work_assistant"})
            assert len(ctx.list_sessions(limit=100)) >= 2

            with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
                mock_orch = MagicMock()
                mock_orch.context_manager = ctx
                mock_get_orch.return_value = mock_orch
                client = TestClient(app)
                response = client.post(
                    "/api/sessions/batch-delete",
                    json={
                        "session_ids": [sid1, sid2],
                        "expected_type": "work_assistant",
                    },
                )
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True
            assert set(data.get("deleted", [])) == {sid1, sid2}
            assert ctx.get_session(sid1) is None
            assert ctx.get_session(sid2) is None
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

    def test_clear_session_messages_success(self, client):
        """测试清除会话消息成功"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.clear_session = MagicMock(return_value=True)
            mock_get_orch.return_value = mock_orch

            response = client.post("/api/sessions/test_session_1/clear")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_create_session_success(self, client):
        """测试创建会话成功"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.create_session = MagicMock(return_value="new_session_id")
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/sessions")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["session_id"] == "new_session_id"
    
    def test_search_sessions_success(self, client, mock_session):
        """测试搜索会话成功"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.list_sessions = MagicMock(return_value=[mock_session])
            mock_orch.context_manager.get_session_preview = MagicMock(return_value={
                "session_id": mock_session.session_id,
                "preview": "测试关键词预览",
                "message_count": 5,
                "created_at": mock_session.created_at.isoformat(),
                "updated_at": mock_session.updated_at.isoformat(),
                "metadata": mock_session.metadata
            })
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/sessions/search?keyword=测试&limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert "sessions" in data
            assert len(data["sessions"]) == 1
    
    def test_search_sessions_no_match(self, client, mock_session):
        """测试搜索会话无匹配"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.list_sessions = MagicMock(return_value=[mock_session])
            mock_orch.context_manager.get_session_preview = MagicMock(return_value={
                "session_id": mock_session.session_id,
                "preview": "不匹配的内容",
                "message_count": 5,
                "created_at": mock_session.created_at.isoformat(),
                "updated_at": mock_session.updated_at.isoformat(),
                "metadata": mock_session.metadata
            })
            mock_get_orch.return_value = mock_orch
            
            response = client.get("/api/sessions/search?keyword=不存在&limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert "sessions" in data
            assert len(data["sessions"]) == 0
    
    def test_generate_session_summary_success(self, client, mock_session, mock_messages):
        """测试生成会话摘要成功"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.get_session = MagicMock(return_value=mock_session)
            mock_orch.context_manager.get_messages = MagicMock(return_value=mock_messages)
            mock_orch.llm_service = MagicMock()
            mock_orch.llm_service.chat = AsyncMock(return_value="这是会话摘要")
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/sessions/test_session_1/summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "summary" in data
    
    def test_generate_session_summary_no_messages(self, client, mock_session):
        """测试生成空会话摘要"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.get_session = MagicMock(return_value=mock_session)
            mock_orch.context_manager.get_messages = MagicMock(return_value=[])
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/sessions/test_session_1/summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "没有消息" in data["error"]

    def test_batch_delete_messages_success(self, client):
        """批量删消息：转发 ContextManager.delete_messages（2026-03-21）"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.delete_messages = MagicMock(
                return_value={"success": True, "deleted": ["m1", "m2"], "failed": []}
            )
            mock_get_orch.return_value = mock_orch

            response = client.post(
                "/api/sessions/test_session_1/messages/batch-delete",
                json={"message_ids": ["m1", "m2"]},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["deleted"] == ["m1", "m2"]
            assert data["failed"] == []
            mock_orch.context_manager.delete_messages.assert_called_once_with(
                "test_session_1", ["m1", "m2"]
            )

    def test_batch_delete_messages_empty_ids(self, client):
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_get_orch.return_value = mock_orch

            response = client.post(
                "/api/sessions/test_session_1/messages/batch-delete",
                json={"message_ids": ["", "  "]},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "不能为空" in data["error"]
            mock_orch.context_manager.delete_messages.assert_not_called()

    def test_batch_delete_sessions_success(self, client):
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.delete_sessions = MagicMock(
                return_value={"success": True, "deleted": ["s1"], "failed": []}
            )
            mock_get_orch.return_value = mock_orch

            response = client.post(
                "/api/sessions/batch-delete",
                json={"session_ids": ["s1"]},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] == ["s1"]
            mock_orch.context_manager.delete_sessions.assert_called_once_with(["s1"])

    def test_batch_delete_sessions_with_expected_type(self, client, mock_session):
        """批量删会话：expected_type 匹配时通过并调用 delete_sessions（2026-03-21）"""
        from copy import deepcopy
        s = deepcopy(mock_session)
        s.metadata = {"type": "article_writing"}
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.get_session = MagicMock(return_value=s)
            mock_orch.context_manager.delete_sessions = MagicMock(
                return_value={"success": True, "deleted": [s.session_id], "failed": []}
            )
            mock_get_orch.return_value = mock_orch

            response = client.post(
                "/api/sessions/batch-delete",
                json={"session_ids": [s.session_id], "expected_type": "article_writing"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("deleted") == [s.session_id]
            mock_orch.context_manager.delete_sessions.assert_called_once_with([s.session_id])

    def test_batch_delete_sessions_article_writing_allows_missing_type(self, client, mock_session):
        """expected_type=article_writing 时允许 metadata 无 type（与 list 过滤一致）"""
        from copy import deepcopy
        s = deepcopy(mock_session)
        s.metadata = {}
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.get_session = MagicMock(return_value=s)
            mock_orch.context_manager.delete_sessions = MagicMock(
                return_value={"success": True, "deleted": [s.session_id], "failed": []}
            )
            mock_get_orch.return_value = mock_orch

            response = client.post(
                "/api/sessions/batch-delete",
                json={"session_ids": [s.session_id], "expected_type": "article_writing"},
            )
            assert response.status_code == 200
            assert response.json().get("success") is True
            mock_orch.context_manager.delete_sessions.assert_called_once_with([s.session_id])

    def test_batch_delete_sessions_expected_type_mismatch(self, client, mock_session):
        """expected_type 与会话 metadata.type 不一致时整单拒绝"""
        from copy import deepcopy
        s = deepcopy(mock_session)
        s.metadata = {"type": "general_chat"}
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.get_session = MagicMock(return_value=s)
            mock_orch.context_manager.delete_sessions = MagicMock()
            mock_get_orch.return_value = mock_orch

            response = client.post(
                "/api/sessions/batch-delete",
                json={"session_ids": [s.session_id], "expected_type": "article_writing"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is False
            assert "不符" in (data.get("error") or "")
            mock_orch.context_manager.delete_sessions.assert_not_called()

    def test_batch_delete_sessions_expected_type_rejects_unknown_session_id(self, client, mock_session):
        """expected_type 模式下任一 id 无索引则整单拒绝，不调用 delete_sessions（2026-03-21 审查闭环）"""
        from copy import deepcopy
        s = deepcopy(mock_session)
        s.metadata = {"type": "work_assistant"}
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.get_session = MagicMock(
                side_effect=lambda sid: s if sid == s.session_id else None
            )
            mock_orch.context_manager.delete_sessions = MagicMock()
            mock_get_orch.return_value = mock_orch

            response = client.post(
                "/api/sessions/batch-delete",
                json={
                    "session_ids": [s.session_id, "ghost-session-id"],
                    "expected_type": "work_assistant",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is False
            assert "ghost-session-id" in (data.get("error") or "")
            assert "expected_type" in (data.get("error") or "")
            mock_orch.context_manager.delete_sessions.assert_not_called()

