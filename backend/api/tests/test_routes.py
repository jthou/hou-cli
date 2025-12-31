"""API 路由测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from backend.main import app


class TestChatRoutes:
    """聊天路由测试"""
    
    def test_chat_endpoint_success(self):
        """测试聊天接口成功"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.process 方法
        print("[MOCK] 测试使用 Mock 数据: orchestrator.process 返回 '测试响应'")
        with patch('backend.api.routes.orchestrator') as mock_orch:
            mock_orch.process = AsyncMock(return_value="测试响应")
            print(f"[MOCK] Mock orchestrator.process 已设置，返回值: '测试响应'")
            
            client = TestClient(app)
            response = client.post("/api/chat", json={"message": "你好"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["response"] == "测试响应"
            mock_orch.process.assert_called_once_with("你好")
            print(f"[MOCK] Mock orchestrator.process 被调用，参数: '你好'")
    
    def test_chat_endpoint_error(self):
        """测试聊天接口错误处理"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.process 抛出异常
        print("[MOCK] 测试使用 Mock 数据: orchestrator.process 抛出异常 '测试错误'")
        with patch('backend.api.routes.orchestrator') as mock_orch:
            mock_orch.process = AsyncMock(side_effect=Exception("测试错误"))
            print(f"[MOCK] Mock orchestrator.process 已设置，将抛出异常: Exception('测试错误')")
            
            client = TestClient(app)
            response = client.post("/api/chat", json={"message": "你好"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "测试错误" in data["error"]
            print(f"[MOCK] Mock orchestrator.process 异常已触发，错误信息: {data['error']}")
    
    def test_chat_stream_endpoint_success(self):
        """测试流式聊天接口成功"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.stream_process 流式响应
        print("[MOCK] 测试使用 Mock 数据: orchestrator.stream_process 返回流式数据 ['chunk1', 'chunk2']")
        async def mock_stream(task):
            print(f"[MOCK] Mock stream_process 被调用，参数: {task}")
            yield "chunk1"
            yield "chunk2"
        
        with patch('backend.api.routes.orchestrator') as mock_orch:
            # 直接设置 stream_process 为异步生成器函数
            mock_orch.stream_process = mock_stream
            print("[MOCK] Mock orchestrator.stream_process 已设置为异步生成器函数")
            
            client = TestClient(app)
            response = client.post("/api/chat/stream", json={"message": "你好"})
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            # 读取流式响应
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            
            assert b"chunk1" in content or b"chunk2" in content
    
    def test_chat_stream_endpoint_error(self):
        """测试流式聊天接口错误处理"""
        # [MOCK] 使用 Mock 数据模拟 orchestrator.stream_process 抛出异常
        print("[MOCK] 测试使用 Mock 数据: orchestrator.stream_process 抛出异常 '测试错误'")
        with patch('backend.api.routes.orchestrator') as mock_orch:
            mock_orch.stream_process = AsyncMock(side_effect=Exception("测试错误"))
            print(f"[MOCK] Mock orchestrator.stream_process 已设置，将抛出异常: Exception('测试错误')")
            
            client = TestClient(app)
            response = client.post("/api/chat/stream", json={"message": "你好"})
            
            assert response.status_code == 200
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            
            assert b"error" in content.lower() or "测试错误".encode('utf-8') in content
            print(f"[MOCK] Mock orchestrator.stream_process 异常已触发，响应内容包含错误信息")


class TestHealthCheck:
    """健康检查测试"""
    
    def test_health_endpoint(self):
        """测试健康检查接口"""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

