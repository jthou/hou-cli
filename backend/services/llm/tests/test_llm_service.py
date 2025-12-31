"""LLMService 测试"""
import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.llm.llm_service import LLMService


class TestLLMService:
    """LLMService 测试类"""
    
    @pytest.fixture
    def service_with_key(self):
        """创建带 API Key 的服务实例"""
        # [MOCK] 使用 Mock 环境变量模拟 API Key
        print("[MOCK] 测试使用 Mock 环境变量: DEEPSEEK_API_KEY='test_key'")
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            service = LLMService()
            print(f"[MOCK] LLMService 已创建，client 状态: {service.client is not None}")
            return service
    
    @pytest.fixture
    def service_without_key(self):
        """创建不带 API Key 的服务实例"""
        # [MOCK] 使用 Mock 环境变量模拟无 API Key
        print("[MOCK] 测试使用 Mock 环境变量: 清空 DEEPSEEK_API_KEY")
        with patch.dict(os.environ, {}, clear=True):
            service = LLMService()
            service.client = None
            print("[MOCK] LLMService 已创建，client 设置为 None")
            return service
    
    @pytest.mark.asyncio
    async def test_chat_with_client(self, service_with_key):
        """测试聊天（有客户端）"""
        # [MOCK] 使用 Mock 数据模拟 OpenAI API 响应
        print("[MOCK] 测试使用 Mock 数据: OpenAI API 响应 '测试响应'")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "测试响应"
        print(f"[MOCK] Mock 响应对象已创建，content: '测试响应'")
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            print("[MOCK] Mock client.chat.completions.create 已设置")
            
            result = await service_with_key.chat(
                system_prompt="系统提示",
                user_prompt="用户提示"
            )
            
            assert result == "测试响应"
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            print(f"[MOCK] Mock create 被调用，参数: model={call_kwargs['model']}, stream={call_kwargs['stream']}, messages数量={len(call_kwargs['messages'])}")
            assert call_kwargs["model"] == "deepseek-chat"
            assert call_kwargs["stream"] is False
            assert len(call_kwargs["messages"]) == 2
    
    @pytest.mark.asyncio
    async def test_chat_without_client(self, service_without_key):
        """测试聊天（无客户端）"""
        result = await service_without_key.chat(
            system_prompt="系统提示",
            user_prompt="用户提示"
        )
        
        assert result == "LLM 服务未配置"
    
    @pytest.mark.asyncio
    async def test_chat_without_system_prompt(self, service_with_key):
        """测试聊天（无系统提示）"""
        # [MOCK] 使用 Mock 数据模拟 OpenAI API 响应（无系统提示）
        print("[MOCK] 测试使用 Mock 数据: OpenAI API 响应 '测试响应'（无系统提示）")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "测试响应"
        print(f"[MOCK] Mock 响应对象已创建，content: '测试响应'")
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            print("[MOCK] Mock client.chat.completions.create 已设置")
            
            result = await service_with_key.chat(user_prompt="用户提示")
            
            assert result == "测试响应"
            call_kwargs = mock_create.call_args[1]
            print(f"[MOCK] Mock create 被调用，messages数量: {len(call_kwargs['messages'])}")
            assert len(call_kwargs["messages"]) == 1
    
    @pytest.mark.asyncio
    async def test_stream_chat_with_client(self, service_with_key):
        """测试流式聊天（有客户端）"""
        # [MOCK] 使用 Mock 数据模拟 OpenAI API 流式响应
        print("[MOCK] 测试使用 Mock 数据: OpenAI API 流式响应 ['chunk1', 'chunk2']")
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "chunk1"
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = "chunk2"
        print("[MOCK] Mock 流式响应块已创建: chunk1, chunk2")
        
        async def mock_stream():
            print("[MOCK] Mock stream 生成器开始生成数据")
            yield mock_chunk1
            yield mock_chunk2
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_stream()
            print("[MOCK] Mock client.chat.completions.create 已设置为流式响应")
            
            chunks = []
            async for chunk in service_with_key.stream_chat(
                system_prompt="系统提示",
                user_prompt="用户提示"
            ):
                chunks.append(chunk)
                print(f"[MOCK] 接收到流式数据块: {chunk}")
            
            assert chunks == ["chunk1", "chunk2"]
            call_kwargs = mock_create.call_args[1]
            print(f"[MOCK] Mock create 被调用，stream={call_kwargs['stream']}")
            assert call_kwargs["stream"] is True
    
    @pytest.mark.asyncio
    async def test_stream_chat_without_client(self, service_without_key):
        """测试流式聊天（无客户端）"""
        chunks = []
        async for chunk in service_without_key.stream_chat(
            system_prompt="系统提示",
            user_prompt="用户提示"
        ):
            chunks.append(chunk)
        
        assert chunks == ["LLM 服务未配置"]

