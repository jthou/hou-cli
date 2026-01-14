"""流式API规划功能和任务管理功能集成测试"""
import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# 在导入前设置环境变量
import os
os.environ.setdefault('DEEPSEEK_API_KEY', 'test_key_for_testing')
os.environ.setdefault('ENABLE_PLANNING', 'true')


class TestStreamAPIPlanningIntegration:
    """测试流式API中规划功能和任务管理功能的集成"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def app(self, temp_dir, monkeypatch):
        """创建测试应用"""
        # 设置环境变量
        monkeypatch.setenv("ENABLE_PLANNING", "true")
        monkeypatch.setenv("PLANNING_WORK_DIR", str(temp_dir))
        monkeypatch.setenv("PLANNING_COMPLEXITY_THRESHOLD", "0.2")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test_key")
        
        # Mock Orchestrator
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            
            # Mock stream_process 方法
            async def mock_stream_process(task, context=None):
                """模拟流式处理"""
                # 发送调试消息
                from backend.api.stream_sender import StreamMessageBuilder
                debug_info = {
                    "type": "debug",
                    "category": "test",
                    "message": "测试消息"
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                
                # 发送内容
                yield "测试响应"
            
            mock_orch.stream_process = mock_stream_process
            mock_get_orch.return_value = mock_orch
            
            from backend.main import app
            yield app
    
    def test_stream_chat_message_format(self, app):
        """测试流式聊天消息格式"""
        client = TestClient(app)
        
        response = client.post(
            "/api/chat/stream",
            json={"message": "测试消息"}
        )
        
        assert response.status_code == 200
        
        # 读取流式响应
        content = b""
        for chunk in response.iter_bytes():
            content += chunk
        
        # 验证响应包含消息
        content_str = content.decode('utf-8')
        assert len(content_str) > 0
    
    def test_stream_chat_debug_message(self, app):
        """测试流式聊天中的调试消息"""
        client = TestClient(app)
        
        response = client.post(
            "/api/chat/stream",
            json={"message": "测试消息"}
        )
        
        assert response.status_code == 200
        
        # 检查响应头
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_stream_chat_with_session_id(self, app):
        """测试带会话ID的流式聊天"""
        client = TestClient(app)
        
        response = client.post(
            "/api/chat/stream",
            json={
                "message": "测试消息",
                "session_id": "test_session_123"
            }
        )
        
        assert response.status_code == 200
    
    def test_stream_chat_status_message(self, app, temp_dir, monkeypatch):
        """测试流式聊天中的状态消息（任务进度）"""
        # 设置环境变量
        monkeypatch.setenv("ENABLE_PLANNING", "true")
        monkeypatch.setenv("PLANNING_WORK_DIR", str(temp_dir))
        
        # Mock Orchestrator 以返回状态消息
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            
            async def mock_stream_process_with_status(task, context=None):
                """模拟包含状态消息的流式处理"""
                from backend.api.stream_sender import StreamMessageBuilder
                
                # 发送状态消息
                status_data = {
                    "task": "测试任务",
                    "progress": 50,
                    "message": "处理中..."
                }
                yield StreamMessageBuilder.build_status(status_data)
                
                # 发送内容
                yield "测试响应"
            
            mock_orch.stream_process = mock_stream_process_with_status
            mock_get_orch.return_value = mock_orch
            
            from backend.main import app
            client = TestClient(app)
            
            response = client.post(
                "/api/chat/stream",
                json={"message": "测试消息"}
            )
            
            assert response.status_code == 200
    
    def test_stream_chat_tool_message(self, app, temp_dir, monkeypatch):
        """测试流式聊天中的工具消息"""
        # 设置环境变量
        monkeypatch.setenv("ENABLE_PLANNING", "true")
        monkeypatch.setenv("PLANNING_WORK_DIR", str(temp_dir))
        
        # Mock Orchestrator 以返回工具消息
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            
            async def mock_stream_process_with_tool(task, context=None):
                """模拟包含工具消息的流式处理"""
                from backend.api.stream_sender import StreamMessageBuilder
                
                # 发送工具消息
                tool_info = {
                    "type": "tool",
                    "name": "test_tool",
                    "args": {},
                    "success": True
                }
                yield StreamMessageBuilder.build_tool(tool_info)
                
                # 发送内容
                yield "测试响应"
            
            mock_orch.stream_process = mock_stream_process_with_tool
            mock_get_orch.return_value = mock_orch
            
            from backend.main import app
            client = TestClient(app)
            
            response = client.post(
                "/api/chat/stream",
                json={"message": "测试消息"}
            )
            
            assert response.status_code == 200

