"""聊天路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


class TestChatRoutes:
    """聊天路由测试类"""
    
    def test_chat_endpoint_success(self, client):
        """测试聊天接口成功"""
        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(return_value="测试响应")
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/chat", json={"message": "你好"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["response"] == "测试响应"
            mock_orch.process.assert_called_once()
            call_args = mock_orch.process.call_args
            assert call_args[0][0] == "你好"
            assert call_args[1]["context"] == {}
    
    def test_chat_endpoint_error(self, client):
        """测试聊天接口错误处理"""
        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(side_effect=Exception("测试错误"))
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/chat", json={"message": "你好"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "测试错误" in data["error"]
    
    def test_chat_endpoint_with_session_id(self, client):
        """测试带 session_id 的聊天接口"""
        test_session_id = "test_session_123"
        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(return_value="带会话ID的响应")
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/chat", json={
                "message": "你好",
                "session_id": test_session_id
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            call_args = mock_orch.process.call_args
            assert call_args[1]["context"]["session_id"] == test_session_id
    
    def test_chat_endpoint_empty_message(self, client):
        """测试空消息处理"""
        response = client.post("/api/chat", json={"message": ""})
        
        # FastAPI 的 Pydantic 可能允许空字符串，但会在业务逻辑中处理
        # 如果返回 200，检查响应中是否有错误信息
        if response.status_code == 200:
            data = response.json()
            # 空消息可能在业务逻辑中被处理，返回错误响应
            assert data.get("status") == "error" or "message" in str(data).lower()
        else:
            # 或者返回验证错误
            assert response.status_code == 422
    
    def test_chat_endpoint_missing_message(self, client):
        """测试缺少 message 字段"""
        response = client.post("/api/chat", json={})
        
        assert response.status_code == 422
    
    def test_chat_stream_endpoint_success(self, client):
        """测试流式聊天接口成功"""
        async def mock_stream(task, context=None):
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
        
        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.stream_process = mock_stream
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/chat/stream", json={"message": "你好"})
            
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            
            # 读取流式响应
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            
            assert b"chunk1" in content
            assert b"chunk2" in content
            assert b"chunk3" in content
    
    def test_chat_stream_endpoint_error(self, client):
        """测试流式聊天接口错误处理"""
        async def mock_stream_error(task, context=None):
            raise Exception("流式处理错误")
            yield  # 永远不会执行
        
        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.stream_process = mock_stream_error
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/chat/stream", json={"message": "你好"})
            
            assert response.status_code == 200
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            
            assert b"error" in content.lower() or "流式处理错误".encode('utf-8') in content
    
    def test_chat_stream_endpoint_with_session_id(self, client):
        """测试带 session_id 的流式聊天接口"""
        test_session_id = "stream_session_456"
        
        async def mock_stream_with_context(task, context=None):
            assert context == {"session_id": test_session_id}
            yield "stream_chunk_A"
            yield "stream_chunk_B"
        
        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.stream_process = mock_stream_with_context
            mock_get_orch.return_value = mock_orch
            
            response = client.post("/api/chat/stream", json={
                "message": "流式消息",
                "session_id": test_session_id
            })
            
            assert response.status_code == 200
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            
            assert b"stream_chunk_A" in content
            assert b"stream_chunk_B" in content

    def test_chat_endpoint_with_model_override(self, client):
        """测试带 model 参数的聊天接口，context 正确传递"""
        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(return_value="使用指定模型的响应")
            mock_get_orch.return_value = mock_orch

            response = client.post("/api/chat", json={
                "message": "你好",
                "model": "reasoning"
            })

            assert response.status_code == 200
            call_args = mock_orch.process.call_args
            assert call_args[1]["context"]["model"] == "reasoning"

    def test_chat_stream_endpoint_with_model_override(self, client):
        """测试流式接口带 model 参数"""
        async def mock_stream_with_model_check(task, context=None):
            assert context.get("model") == "code"
            yield "chunk1"
            yield "chunk2"

        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.stream_process = mock_stream_with_model_check
            mock_get_orch.return_value = mock_orch

            response = client.post("/api/chat/stream", json={
                "message": "写一个函数",
                "model": "code"
            })

            assert response.status_code == 200
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            assert b"chunk1" in content

    def test_chat_endpoint_without_model_uses_empty_context(self, client):
        """不传 model 时 context 不包含 model 键"""
        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.process = AsyncMock(return_value="响应")

            def check_context(message, context=None):
                assert context is not None
                assert "model" not in context or context.get("model") is None
                return "响应"

            mock_orch.process.side_effect = check_context
            mock_get_orch.return_value = mock_orch

            response = client.post("/api/chat", json={"message": "你好"})
            assert response.status_code == 200

    def test_chat_stream_image_generation_markdown_in_response(self, client):
        """E2E：图片生成时流式响应应包含 base64 图片的 Markdown 语法"""
        img_b64 = "data:image/png;base64,iVBORw0KGgo="
        image_markdown = f"\n\n![生成的图片]({img_b64})\n\n"

        async def mock_stream_with_image(task, context=None):
            yield "__DEBUG__:{}"
            yield image_markdown

        with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
            mock_orch = MagicMock()
            mock_orch.stream_process = mock_stream_with_image
            mock_get_orch.return_value = mock_orch

            response = client.post(
                "/api/chat/stream",
                json={"message": "画一只猫"},
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
            content_str = content.decode("utf-8")
            assert "![生成的图片]" in content_str
            assert img_b64 in content_str

