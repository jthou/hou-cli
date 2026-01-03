"""Orchestrator 工具集成测试"""
import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.auth.jwt_auth import JWTAuth
from backend.core.agent.tools.builtin.weather_tool import get_weather_tool


class TestOrchestratorToolIntegration:
    """测试 Orchestrator 与工具集成"""
    
    @pytest.fixture
    def jwt_auth(self):
        """创建 JWT 认证实例"""
        try:
            auth = JWTAuth.from_env(
                issuer="test_issuer",
                audience="test_audience",
                subject="test_subject"
            )
            return auth
        except Exception:
            pytest.skip("JWT auth not configured. Set WEATHER_JWT_PRIVATE_KEY in .env")
    
    @pytest.fixture
    def orchestrator(self, jwt_auth):
        """创建 Orchestrator 实例并注册天气工具"""
        orchestrator = Orchestrator()
        
        # 注册天气工具
        weather_tool = get_weather_tool(jwt_auth)
        orchestrator.tool_registry.register(weather_tool)
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_orchestrator_has_tool_registry(self, orchestrator):
        """测试 Orchestrator 有 ToolRegistry"""
        assert hasattr(orchestrator, 'tool_registry')
        assert orchestrator.tool_registry is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_tools_registered(self, orchestrator):
        """测试工具已注册"""
        tools = orchestrator.tool_registry.list_tools()
        assert "get_weather" in tools
    
    @pytest.mark.asyncio
    async def test_llm_can_call_weather_tool(self, orchestrator):
        """测试 LLM 可以调用天气工具"""
        # Mock LLM 响应：返回工具调用请求
        mock_tool_call = {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"location": "北京", "days": 1}'
            }
        }
        
        # Mock API 响应
        search_response = {
            "code": "200",
            "location": [{"name": "北京", "id": "101010100"}]
        }
        weather_response = {
            "code": "200",
            "now": {"temp": "20", "text": "晴", "windDir": "北风"}
        }
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = [search_response, weather_response]
            
            # Mock LLM 第一次调用：返回工具调用
            with patch.object(orchestrator.llm_service.client.chat.completions, 'create') as mock_create:
                # 第一次调用：返回工具调用
                mock_response_1 = AsyncMock()
                mock_response_1.choices = [MagicMock()]
                mock_response_1.choices[0].message = MagicMock()
                mock_response_1.choices[0].message.content = None
                mock_response_1.choices[0].message.tool_calls = [MagicMock()]
                mock_response_1.choices[0].message.tool_calls[0].id = "call_123"
                mock_response_1.choices[0].message.tool_calls[0].type = "function"
                mock_response_1.choices[0].message.tool_calls[0].function = MagicMock()
                mock_response_1.choices[0].message.tool_calls[0].function.name = "get_weather"
                mock_response_1.choices[0].message.tool_calls[0].function.arguments = '{"location": "北京", "days": 1}'
                
                # 第二次调用：返回最终回复
                mock_response_2 = AsyncMock()
                mock_response_2.choices = [MagicMock()]
                mock_response_2.choices[0].message = MagicMock()
                mock_response_2.choices[0].message.content = "北京今天天气晴朗，温度20度，北风。"
                mock_response_2.choices[0].message.tool_calls = None
                
                mock_create.side_effect = [mock_response_1, mock_response_2]
                
                # 执行
                result = await orchestrator.process("查北京的天气", {"session_id": "test_session"})
                
                # 验证
                assert "北京" in result or "天气" in result or "20" in result or "晴" in result
                assert mock_create.call_count == 2  # 应该调用两次：工具调用 + 最终回复

