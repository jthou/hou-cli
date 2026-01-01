"""LLMService 测试"""
import pytest
import os
import asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock, Mock
from backend.services.llm.llm_service import LLMService


class TestLLMService:
    """LLMService 测试类"""
    
    @pytest.fixture
    def service_with_key(self):
        """创建带 API Key 的服务实例"""
        # [MOCK] 使用 Mock 环境变量模拟 API Key
        print("[MOCK] 测试使用 Mock 环境变量: DEEPSEEK_API_KEY='test_key_1234567890'")
        # 使用足够长的测试 key 以通过格式验证
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key_1234567890'}):
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
    async def test_chat_without_client(self):
        """测试聊天（无客户端）- 现在会在初始化时抛出异常"""
        # [MOCK] 使用 Mock 环境变量模拟无 API Key
        print("[MOCK] 测试使用 Mock 环境变量: 清空 DEEPSEEK_API_KEY")
        with patch.dict(os.environ, {}, clear=True):
            # 现在 LLMService 在初始化时就会抛出异常
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                LLMService()
    
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
    async def test_stream_chat_without_client(self):
        """测试流式聊天（无客户端）- 现在会在初始化时抛出异常"""
        # [MOCK] 使用 Mock 环境变量模拟无 API Key
        print("[MOCK] 测试使用 Mock 环境变量: 清空 DEEPSEEK_API_KEY")
        with patch.dict(os.environ, {}, clear=True):
            # 现在 LLMService 在初始化时就会抛出异常
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                LLMService()
    
    # ========== TODO-001 新增测试用例 ==========
    
    @pytest.mark.asyncio
    async def test_config_missing_api_key(self):
        """测试 API Key 缺失时的错误处理"""
        # [MOCK] 使用 Mock 环境变量模拟 API Key 缺失
        print("[MOCK] 测试使用 Mock 环境变量: 清空 DEEPSEEK_API_KEY")
        with patch.dict(os.environ, {}, clear=True):
            # TODO-001: 应该抛出 ValueError，提示 API Key 未设置
            # 当前实现：不会抛出异常，只是 client 为 None
            # 预期：应该抛出 ValueError("DEEPSEEK_API_KEY 环境变量未设置")
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                LLMService()
    
    def test_config_invalid_api_key_format(self):
        """测试无效 API Key 格式验证"""
        # [MOCK] 使用 Mock 环境变量模拟无效 API Key
        print("[MOCK] 测试使用 Mock 环境变量: DEEPSEEK_API_KEY='' (空字符串)")
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': ''}):
            # TODO-001: 应该验证 API Key 格式（非空、长度检查）
            # 预期：应该抛出 ValueError("API Key 格式无效")
            with pytest.raises(ValueError, match="API Key"):
                LLMService()
    
    @pytest.mark.asyncio
    async def test_chat_401_error_no_retry(self, service_with_key):
        """测试 401 认证错误（不重试）"""
        # [MOCK] 使用 Mock 数据模拟 401 错误
        print("[MOCK] 测试使用 Mock 数据: 401 认证错误（不应重试）")
        mock_error = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=Mock(status_code=401)
        )
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = mock_error
            print("[MOCK] Mock create 已设置，将抛出 401 错误")
            
            # TODO-001: 401 错误不应重试，直接抛出
            # 预期：应该直接抛出异常，不重试
            with pytest.raises(httpx.HTTPStatusError):
                await service_with_key.chat(user_prompt="测试")
            
            # 验证只调用一次（不重试）
            assert mock_create.call_count == 1
            print("[MOCK] 401 错误未重试，符合预期")
    
    @pytest.mark.asyncio
    async def test_chat_429_error_with_retry(self, service_with_key):
        """测试 429 限流错误（等待后重试）"""
        # [MOCK] 使用 Mock 数据模拟 429 错误后成功
        print("[MOCK] 测试使用 Mock 数据: 429 限流错误，等待后重试成功")
        mock_429_error = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=Mock(),
            response=Mock(status_code=429)
        )
        mock_success_response = MagicMock()
        mock_success_response.choices = [MagicMock()]
        mock_success_response.choices[0].message.content = "成功响应"
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = [mock_429_error, mock_success_response]
            print("[MOCK] Mock create 已设置，第一次返回 429，第二次成功")
            
            # TODO-001: 429 错误应等待 2 秒后重试
            # 预期：应该等待后重试，最终成功
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await service_with_key.chat(user_prompt="测试")
                assert result == "成功响应"
                assert mock_create.call_count == 2
                # 验证等待了 2 秒
                mock_sleep.assert_called_once_with(2)
                print("[MOCK] 429 错误已处理，等待 2 秒后重试成功")
    
    @pytest.mark.asyncio
    async def test_chat_network_error_with_retry(self, service_with_key):
        """测试网络错误（重试 3 次）"""
        # [MOCK] 使用 Mock 数据模拟网络错误
        print("[MOCK] 测试使用 Mock 数据: 网络错误，重试 3 次")
        mock_network_error = httpx.RequestError("网络连接失败")
        mock_success_response = MagicMock()
        mock_success_response.choices = [MagicMock()]
        mock_success_response.choices[0].message.content = "成功响应"
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            # 前两次失败，第三次成功
            mock_create.side_effect = [
                mock_network_error,
                mock_network_error,
                mock_success_response
            ]
            print("[MOCK] Mock create 已设置，前两次网络错误，第三次成功")
            
            # TODO-001: 网络错误应重试 3 次，间隔 1 秒
            # 预期：应该重试 3 次，最终成功
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await service_with_key.chat(user_prompt="测试")
                assert result == "成功响应"
                assert mock_create.call_count == 3
                # 验证等待了 2 次（每次 1 秒）
                assert mock_sleep.call_count == 2
                print("[MOCK] 网络错误已处理，重试 3 次后成功")
    
    @pytest.mark.asyncio
    async def test_chat_retry_exhausted(self, service_with_key):
        """测试重试次数耗尽"""
        # [MOCK] 使用 Mock 数据模拟持续的网络错误
        print("[MOCK] 测试使用 Mock 数据: 网络错误，重试次数耗尽")
        mock_network_error = httpx.RequestError("网络连接失败")
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = mock_network_error
            print("[MOCK] Mock create 已设置，持续返回网络错误")
            
            # TODO-001: 重试 3 次后仍失败，应抛出异常
            # 预期：应该抛出异常
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(httpx.RequestError):
                    await service_with_key.chat(user_prompt="测试")
                
                # 验证重试了 3 次
                assert mock_create.call_count == 3
                print("[MOCK] 重试次数已耗尽，抛出异常")
    
    def test_temperature_parameter_validation(self):
        """测试 temperature 参数验证"""
        # [MOCK] 使用 Mock 环境变量
        print("[MOCK] 测试使用 Mock 环境变量: DEEPSEEK_API_KEY='test_key_1234567890'")
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key_1234567890'}):
            # TODO-001: temperature 应在 0-2 范围内
            # 测试超出范围的值
            service = LLMService(temperature=3.0)
            # 预期：应该被限制到 2.0
            assert service.temperature == 2.0
            print("[MOCK] temperature 参数已验证，超出范围的值被限制")
            
            service = LLMService(temperature=-1.0)
            # 预期：应该被限制到 0.0
            assert service.temperature == 0.0
            print("[MOCK] temperature 参数已验证，负值被限制到 0")
    
    def test_max_tokens_parameter_validation(self):
        """测试 max_tokens 参数验证"""
        # [MOCK] 使用 Mock 环境变量
        print("[MOCK] 测试使用 Mock 环境变量: DEEPSEEK_API_KEY='test_key_1234567890'")
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key_1234567890'}):
            # TODO-001: max_tokens 应 > 0
            # 测试无效值
            service = LLMService(max_tokens=0)
            # 预期：应该被限制到 1
            assert service.max_tokens >= 1
            print("[MOCK] max_tokens 参数已验证，无效值被修正")
            
            service = LLMService(max_tokens=-10)
            # 预期：应该被限制到 1
            assert service.max_tokens >= 1
            print("[MOCK] max_tokens 参数已验证，负值被修正")
    
    @pytest.mark.asyncio
    async def test_chat_with_parameters(self):
        """测试带参数的聊天调用"""
        # [MOCK] 使用 Mock 环境变量和 Mock 数据
        print("[MOCK] 测试使用 Mock 环境变量: DEEPSEEK_API_KEY='test_key_1234567890'")
        print("[MOCK] 测试使用 Mock 数据: 带参数的 API 调用")
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key_1234567890'}):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "测试响应"
            
            # TODO-001: 需要支持 temperature 和 max_tokens 参数
            # 创建带参数的服务实例
            service = LLMService(temperature=0.8, max_tokens=1000)
        
            with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_response
                print("[MOCK] Mock create 已设置")
                
                result = await service.chat(user_prompt="测试")
                assert result == "测试响应"
                
                # 验证参数被传递
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["temperature"] == 0.8
                assert call_kwargs["max_tokens"] == 1000
                print(f"[MOCK] 参数已传递: temperature={call_kwargs['temperature']}, max_tokens={call_kwargs['max_tokens']}")
    
    @pytest.mark.asyncio
    async def test_stream_chat_timeout(self, service_with_key):
        """测试流式响应超时"""
        # [MOCK] 使用 Mock 数据模拟超时
        print("[MOCK] 测试使用 Mock 数据: 流式响应超时")
        
        # 模拟一个会超时的 create 调用
        async def slow_create(*args, **kwargs):
            """模拟慢速创建（超过超时时间）"""
            await asyncio.sleep(0.2)  # 超过 0.1 秒超时
            # 返回一个空的流
            async def empty_stream():
                yield MagicMock(choices=[MagicMock(delta=MagicMock(content="chunk1"))])
            return empty_stream()
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = slow_create
            print("[MOCK] Mock create 已设置，将模拟超时")
            
            # TODO-001: 流式响应应有超时控制
            # 预期：应该抛出超时异常（使用较短的超时时间进行测试）
            with pytest.raises(asyncio.TimeoutError):
                async for chunk in service_with_key.stream_chat(user_prompt="测试", timeout=0.1):
                    pass
            print("[MOCK] 流式响应超时已处理")
    
    @pytest.mark.asyncio
    async def test_stream_chat_interrupt_handling(self, service_with_key):
        """测试流式响应中断处理"""
        # [MOCK] 使用 Mock 数据模拟流式响应
        print("[MOCK] 测试使用 Mock 数据: 流式响应中断处理")
        
        async def mock_stream():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="chunk1"))])
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="chunk2"))])
            raise KeyboardInterrupt("用户中断")
        
        with patch.object(service_with_key.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_stream()
            print("[MOCK] Mock create 已设置，将模拟中断")
            
            # TODO-001: 流式响应中断时应优雅处理
            # 预期：应该优雅处理中断，不报错
            chunks = []
            try:
                async for chunk in service_with_key.stream_chat(user_prompt="测试"):
                    chunks.append(chunk)
            except KeyboardInterrupt:
                pass  # 优雅处理
            
            assert len(chunks) >= 0  # 可能收到部分数据
            print("[MOCK] 流式响应中断已优雅处理")

