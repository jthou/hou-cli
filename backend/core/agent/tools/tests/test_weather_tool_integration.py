"""天气工具集成测试（Tool 注册和 Function Calling）"""
import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.auth.jwt_auth import JWTAuth, JWTAuthError
from backend.core.agent.tools.builtin.weather_tool import WeatherTool, WeatherToolError

# 加载 .env：与 backend/main.py 一致——用户配置目录、项目根、当前目录
_env_paths = [
    Path.home() / ".config" / "hou-cli" / ".env",
    Path(__file__).resolve().parents[5] / ".env",
    Path.cwd() / ".env",
]
for _env in _env_paths:
    if _env.exists():
        load_dotenv(_env, override=True)
        break
else:
    load_dotenv()


class TestWeatherToolIntegration:
    """测试天气工具集成（Tool 基类和注册）"""
    
    @pytest.fixture
    def jwt_auth(self):
        """创建 JWT 认证实例"""
        try:
            # JWTAuth.from_env() 会从环境变量读取：
            # - WEATHER_JWT_PRIVATE_KEY: 私钥
            # - QWEATHER_CREDENTIAL_ID: 凭据ID (kid)
            # - QWEATHER_PROJECT_ID: 项目ID (sub)
            auth = JWTAuth.from_env()
            return auth
        except Exception as e:
            pytest.skip(f"JWT auth not configured: {str(e)}. Set WEATHER_JWT_PRIVATE_KEY, QWEATHER_CREDENTIAL_ID, QWEATHER_PROJECT_ID in .env")
    
    @pytest.fixture
    def weather_tool_instance(self, jwt_auth):
        """创建 WeatherTool 实例"""
        return WeatherTool(jwt_auth=jwt_auth)
    
    def test_weather_tool_implements_tool_interface(self, weather_tool_instance):
        """测试 WeatherTool 可以作为 Tool 使用（需要包装）"""
        # WeatherTool 本身不是 Tool，需要包装成 Tool
        # 这个测试验证 WeatherTool 的接口可以被 Tool 包装
        assert hasattr(weather_tool_instance, 'get_current_weather')
        assert hasattr(weather_tool_instance, 'get_forecast')
        assert hasattr(weather_tool_instance, 'search_city')
    
    def test_weather_tool_can_be_wrapped_as_tool(self, weather_tool_instance, jwt_auth):
        """测试 WeatherTool 可以被包装成 Tool"""
        from backend.core.agent.tools.builtin.weather_tool import get_weather_tool
        
        tool = get_weather_tool(jwt_auth)
        assert isinstance(tool, Tool)
        assert tool.name == "get_weather"
    
    def test_weather_tool_parameters(self, jwt_auth):
        """测试天气工具的参数定义"""
        from backend.core.agent.tools.builtin.weather_tool import get_weather_tool
        
        tool = get_weather_tool(jwt_auth)
        assert len(tool.parameters) == 2
        
        # 检查 location 参数
        location_param = next((p for p in tool.parameters if p.name == "location"), None)
        assert location_param is not None
        assert location_param.type == "string"
        assert location_param.required is True
        
        # 检查 days 参数
        days_param = next((p for p in tool.parameters if p.name == "days"), None)
        assert days_param is not None
        assert days_param.type == "integer"
        assert days_param.required is False
        assert days_param.default == 1
    
    def test_weather_tool_execute_success(self, jwt_auth):
        """测试天气工具执行成功"""
        from backend.core.agent.tools.builtin.weather_tool import get_weather_tool
        from unittest.mock import patch
        
        tool = get_weather_tool(jwt_auth)
        
        # Mock API 响应
        search_response = {
            "code": "200",
            "location": [{"name": "北京", "id": "101010100"}]
        }
        weather_response = {
            "code": "200",
            "now": {"temp": "20", "text": "晴"}
        }
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = [search_response, weather_response]
            
            result = tool.execute(location="北京", days=1)
            assert isinstance(result, ToolResult)
            assert result.success is True
            assert result.data is not None
            assert "current" in result.data
            assert result.data["current"]["temp"] == "20"
    
    def test_weather_tool_execute_city_not_found(self, jwt_auth):
        """测试天气工具执行时城市未找到"""
        from backend.core.agent.tools.builtin.weather_tool import get_weather_tool
        from unittest.mock import patch
        
        tool = get_weather_tool(jwt_auth)
        
        # Mock 城市未找到
        search_response = {
            "code": "404",
            "location": []
        }
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = search_response
            
            result = tool.execute(location="不存在的城市")
            assert isinstance(result, ToolResult)
            assert result.success is False
            assert result.error is not None
            assert "not found" in result.error.lower()
    
    def test_weather_tool_registration(self, jwt_auth):
        """测试天气工具注册到 ToolRegistry"""
        from backend.core.agent.tools.builtin.weather_tool import get_weather_tool
        from backend.core.agent.tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        registry.clear()
        
        tool = get_weather_tool(jwt_auth)
        registry.register(tool)
        
        # 验证工具已注册
        retrieved = registry.get_tool("get_weather")
        assert retrieved is not None
        assert retrieved.name == "get_weather"
    
    def test_weather_tool_llm_format(self, jwt_auth):
        """测试天气工具的 LLM 格式定义"""
        from backend.core.agent.tools.builtin.weather_tool import get_weather_tool
        from backend.core.agent.tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        registry.clear()
        
        tool = get_weather_tool(jwt_auth)
        registry.register(tool)
        
        llm_tools = registry.get_tools_for_llm()
        assert len(llm_tools) == 1
        
        llm_tool = llm_tools[0]
        assert llm_tool["type"] == "function"
        assert llm_tool["function"]["name"] == "get_weather"
        assert "parameters" in llm_tool["function"]
        assert "properties" in llm_tool["function"]["parameters"]
        assert "location" in llm_tool["function"]["parameters"]["properties"]
        assert "days" in llm_tool["function"]["parameters"]["properties"]


class TestWeatherToolLiveEnv:
    """使用 .env 配置的真实和风 API 请求（未配置时跳过）"""

    def _skip_if_no_env(self):
        if not os.getenv("WEATHER_JWT_PRIVATE_KEY") or not os.getenv("QWEATHER_API_HOST"):
            pytest.skip("需要 .env 中配置 WEATHER_JWT_PRIVATE_KEY、QWEATHER_CREDENTIAL_ID、QWEATHER_PROJECT_ID、QWEATHER_API_HOST")
        try:
            JWTAuth.from_env()
        except JWTAuthError as e:
            pytest.skip(f"和风 JWT 未配置完整: {e}")

    def test_get_current_weather_live(self):
        """使用 .env 调用和风实时天气 API，校验返回结构"""
        self._skip_if_no_env()
        auth = JWTAuth.from_env()
        tool = WeatherTool(jwt_auth=auth)
        try:
            data = tool.get_current_weather("北京")
        except WeatherToolError as e:
            if "401" in str(e):
                pytest.skip(f"和风 API 返回 401，请检查 .env 中 JWT 配置: {e}")
            raise
        assert data.get("code") == "200", data
        assert "now" in data, data
        now = data["now"]
        assert "temp" in now
        assert "text" in now

    def test_get_forecast_live(self):
        """使用 .env 调用和风预报 API，校验返回结构"""
        self._skip_if_no_env()
        auth = JWTAuth.from_env()
        tool = WeatherTool(jwt_auth=auth)
        try:
            data = tool.get_forecast("上海", days=3)
        except WeatherToolError as e:
            if "401" in str(e):
                pytest.skip(f"和风 API 返回 401，请检查 .env 中 JWT 配置: {e}")
            raise
        assert data.get("code") == "200", data
        assert "daily" in data, data
        assert len(data["daily"]) >= 1

