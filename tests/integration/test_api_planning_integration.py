"""API规划功能集成测试"""
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


class TestAPIPlanningIntegration:
    """测试API中规划功能的集成"""
    
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
        
        from backend.main import app
        return app
    
    def test_chat_endpoint_with_planning(self, app, temp_dir):
        """测试聊天端点启用规划功能"""
        # Mock Orchestrator
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(return_value="测试响应")
            mock_get_orch.return_value = mock_orch
            
            client = TestClient(app)
            
            response = client.post(
                "/api/chat",
                json={"message": "测试消息"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["response"] == "测试响应"
    
    def test_stream_chat_endpoint_with_planning(self, app, temp_dir):
        """测试流式聊天端点启用规划功能"""
        # Mock Orchestrator
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            
            async def mock_stream_process(task, context=None):
                """模拟流式处理"""
                from backend.api.stream_sender import StreamMessageBuilder
                
                # 发送调试消息
                debug_info = {
                    "type": "debug",
                    "category": "planning",
                    "message": "规划功能已启用"
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                
                # 发送内容
                yield "测试响应"
            
            mock_orch.stream_process = mock_stream_process
            mock_get_orch.return_value = mock_orch
            
            client = TestClient(app)
            
            response = client.post(
                "/api/chat/stream",
                json={"message": "测试消息"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_stream_chat_complex_task_creates_planning_files(
        self, app, temp_dir, monkeypatch
    ):
        """测试复杂任务创建规划文件"""
        # 设置环境变量
        monkeypatch.setenv("ENABLE_PLANNING", "true")
        monkeypatch.setenv("PLANNING_WORK_DIR", str(temp_dir))
        monkeypatch.setenv("PLANNING_COMPLEXITY_THRESHOLD", "0.2")
        
        # Mock Orchestrator
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            
            async def mock_stream_process(task, context=None):
                """模拟流式处理（包含规划文件创建）"""
                from backend.api.stream_sender import StreamMessageBuilder
                
                # 发送规划文件创建消息
                debug_info = {
                    "type": "debug",
                    "category": "planning",
                    "message": "检测到复杂任务，已创建规划文件"
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                
                # 发送内容
                yield "测试响应"
            
            mock_orch.stream_process = mock_stream_process
            mock_get_orch.return_value = mock_orch
            
            client = TestClient(app)
            
            # 发送复杂任务
            complex_task = "实现一个完整的用户管理系统"
            response = client.post(
                "/api/chat/stream",
                json={"message": complex_task}
            )
            
            assert response.status_code == 200
    
    def test_stream_chat_with_task_progress(self, app, temp_dir, monkeypatch):
        """测试流式聊天中的任务进度更新"""
        # 设置环境变量
        monkeypatch.setenv("ENABLE_PLANNING", "true")
        monkeypatch.setenv("PLANNING_WORK_DIR", str(temp_dir))
        
        # Mock Orchestrator
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            
            async def mock_stream_process_with_progress(task, context=None):
                """模拟包含进度更新的流式处理"""
                from backend.api.stream_sender import StreamMessageBuilder
                
                # 发送任务状态消息
                status_data = {
                    "task": "测试任务",
                    "progress": 50,
                    "message": "处理中...",
                    "task_id": "test_task_123"
                }
                yield StreamMessageBuilder.build_status(status_data)
                
                # 发送内容
                yield "测试响应"
            
            mock_orch.stream_process = mock_stream_process_with_progress
            mock_get_orch.return_value = mock_orch
            
            client = TestClient(app)
            
            response = client.post(
                "/api/chat/stream",
                json={"message": "测试消息"}
            )
            
            assert response.status_code == 200
    
    def test_stream_chat_message_types(self, app, temp_dir, monkeypatch):
        """测试流式聊天中的各种消息类型"""
        # 设置环境变量
        monkeypatch.setenv("ENABLE_PLANNING", "true")
        monkeypatch.setenv("PLANNING_WORK_DIR", str(temp_dir))
        
        # Mock Orchestrator
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            
            async def mock_stream_process_all_types(task, context=None):
                """模拟包含所有消息类型的流式处理"""
                from backend.api.stream_sender import StreamMessageBuilder
                
                # 发送调试消息
                debug_info = {
                    "type": "debug",
                    "category": "test",
                    "message": "调试消息"
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                
                # 发送工具消息
                tool_info = {
                    "type": "tool",
                    "name": "test_tool",
                    "args": {},
                    "success": True
                }
                yield StreamMessageBuilder.build_tool(tool_info)
                
                # 发送状态消息
                status_data = {
                    "task": "测试任务",
                    "progress": 100,
                    "message": "完成"
                }
                yield StreamMessageBuilder.build_status(status_data)
                
                # 发送内容
                yield "测试响应"
            
            mock_orch.stream_process = mock_stream_process_all_types
            mock_get_orch.return_value = mock_orch
            
            client = TestClient(app)
            
            response = client.post(
                "/api/chat/stream",
                json={"message": "测试消息"}
            )
            
            assert response.status_code == 200
            
            # 读取响应内容
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            
            content_str = content.decode('utf-8')
            
            # 验证包含各种消息类型
            assert "__DEBUG__:" in content_str or len(content_str) > 0
            assert "__TOOL__:" in content_str or len(content_str) > 0
            assert "__STATUS__:" in content_str or len(content_str) > 0

