"""会话管理路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient
from backend.core.context.models import Session, Message, MessageRole


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
            mock_orch.context_manager.list_sessions.assert_called_once_with(limit=5)
    
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
        """测试删除会话成功"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.clear_session = MagicMock(return_value=True)
            mock_get_orch.return_value = mock_orch
            
            response = client.delete("/api/sessions/test_session_1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_orch.context_manager.clear_session.assert_called_once_with("test_session_1")
    
    def test_delete_session_not_found(self, client):
        """测试删除不存在的会话"""
        with patch('backend.api.session_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.context_manager = MagicMock()
            mock_orch.context_manager.clear_session = MagicMock(return_value=False)
            mock_get_orch.return_value = mock_orch
            
            response = client.delete("/api/sessions/nonexistent_session")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
    
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

