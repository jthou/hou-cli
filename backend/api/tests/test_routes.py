"""API 路由测试"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

# 在导入 backend.main 之前设置环境变量，避免 LLMService 初始化失败
os.environ.setdefault('DEEPSEEK_API_KEY', 'test_key_for_testing_1234567890')

# 确保在导入前设置环境变量
from backend.main import app


class TestChatRoutes:
    """聊天路由测试"""
    
    def test_chat_endpoint_success(self):
        """测试聊天接口成功"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.process 方法
        print("[MOCK] 测试使用 Mock 数据: orchestrator.process 返回 '测试响应'")
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(return_value="测试响应")
            mock_get_orch.return_value = mock_orch
            print(f"[MOCK] Mock orchestrator.process 已设置，返回值: '测试响应'")
            
            client = TestClient(app)
            response = client.post("/api/chat", json={"message": "你好"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["response"] == "测试响应"
            mock_orch.process.assert_called_once_with("你好", context={})
            print(f"[MOCK] Mock orchestrator.process 被调用，参数: '你好', context={{}}")
    
    def test_chat_endpoint_error(self):
        """测试聊天接口错误处理"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.process 抛出异常
        print("[MOCK] 测试使用 Mock 数据: orchestrator.process 抛出异常 '测试错误'")
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(side_effect=Exception("测试错误"))
            mock_get_orch.return_value = mock_orch
            print(f"[MOCK] Mock orchestrator.process 已设置，将抛出异常: Exception('测试错误')")

            client = TestClient(app)
            response = client.post("/api/chat", json={"message": "你好"})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "测试错误" in data["error"]
            print(f"[MOCK] Mock orchestrator.process 异常已触发，错误信息: {data['error']}")
    
    def test_chat_endpoint_with_session_id(self):
        """测试带 session_id 的聊天接口"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.process 方法，带 session_id
        print("[MOCK] 测试使用 Mock 数据: orchestrator.process 返回 '带会话ID的响应'")
        test_session_id = "test_session_123"
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(return_value="带会话ID的响应")
            mock_get_orch.return_value = mock_orch
            print(f"[MOCK] Mock orchestrator.process 已设置，返回值: '带会话ID的响应'")

            client = TestClient(app)
            response = client.post("/api/chat", json={"message": "你好", "session_id": test_session_id})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["response"] == "带会话ID的响应"
            mock_orch.process.assert_called_once_with("你好", context={"session_id": test_session_id})
            print(f"[MOCK] Mock orchestrator.process 被调用，参数: '你好', context={{'session_id': '{test_session_id}'}}")
    
    def test_chat_stream_endpoint_success(self):
        """测试流式聊天接口成功"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.stream_process 流式响应
        print("[MOCK] 测试使用 Mock 数据: orchestrator.stream_process 返回流式数据 ['chunk1', 'chunk2']")
        async def mock_stream(task, context=None):
            print(f"[MOCK] Mock stream_process 被调用，参数: {task}, context={context}")
            yield "chunk1"
            yield "chunk2"
        
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.stream_process = mock_stream
            mock_get_orch.return_value = mock_orch
            print("[MOCK] Mock orchestrator.stream_process 已设置为异步生成器函数")
            
            client = TestClient(app)
            response = client.post("/api/chat/stream", json={"message": "你好"})
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            # 读取流式响应
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            
            assert b"chunk1" in content and b"chunk2" in content
            print(f"[MOCK] 流式响应内容包含 'chunk1' 和 'chunk2'")
    
    def test_chat_stream_endpoint_error(self):
        """测试流式聊天接口错误处理"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.stream_process 抛出异常
        print("[MOCK] 测试使用 Mock 数据: orchestrator.stream_process 抛出异常 '测试错误'")
        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.stream_process = AsyncMock(side_effect=Exception("测试错误"))
            mock_get_orch.return_value = mock_orch
            print(f"[MOCK] Mock orchestrator.stream_process 已设置，将抛出异常: Exception('测试错误')")

            client = TestClient(app)
            response = client.post("/api/chat/stream", json={"message": "你好"})

            assert response.status_code == 200
            content = b""
            for chunk in response.iter_bytes():
                content += chunk

            assert b"error" in content.lower() or "测试错误".encode('utf-8') in content
            print(f"[MOCK] Mock orchestrator.stream_process 异常已触发，响应内容包含错误信息")
    
    def test_chat_stream_endpoint_with_session_id(self):
        """测试带 session_id 的流式聊天接口"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.stream_process 流式响应，带 session_id
        print("[MOCK] 测试使用 Mock 数据: orchestrator.stream_process 返回流式数据，带 session_id")
        test_session_id = "stream_session_456"
        async def mock_stream_with_context(task, context=None):
            print(f"[MOCK] Mock stream_process 被调用，参数: {task}, context={context}")
            assert context == {"session_id": test_session_id}
            yield "stream_chunk_A"
            yield "stream_chunk_B"

        with patch('backend.api.routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.stream_process = mock_stream_with_context
            mock_get_orch.return_value = mock_orch
            print("[MOCK] Mock orchestrator.stream_process 已设置为异步生成器函数，带上下文验证")

            client = TestClient(app)
            response = client.post("/api/chat/stream", json={"message": "流式消息", "session_id": test_session_id})

            assert response.status_code == 200
            content = b""
            for chunk in response.iter_bytes():
                content += chunk

            assert b"stream_chunk_A" in content and b"stream_chunk_B" in content
            print(f"[MOCK] 流式响应内容包含 'stream_chunk_A' 和 'stream_chunk_B'，session_id 已传递")


class TestHealthCheck:
    """健康检查测试"""
    
    def test_health_endpoint(self):
        """测试健康检查接口"""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
