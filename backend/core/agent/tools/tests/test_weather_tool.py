"""天气工具测试"""
import pytest
import os
from unittest.mock import patch, MagicMock, Mock
from shared.load_env import load_env_for_file
from backend.core.agent.tools.builtin.weather_tool import WeatherTool, WeatherToolError
from backend.core.agent.tools.auth.jwt_auth import JWTAuth

load_env_for_file(__file__)


class TestWeatherTool:
    """测试 WeatherTool 类"""
    
    @pytest.fixture
    def jwt_auth(self):
        """创建 JWT 认证实例"""
        try:
            auth = JWTAuth.from_env()
            return auth
        except Exception:
            pytest.skip("JWT auth not configured. Set WEATHER_JWT_PRIVATE_KEY, QWEATHER_CREDENTIAL_ID, QWEATHER_PROJECT_ID in .env")
    
    @pytest.fixture
    def weather_tool(self, jwt_auth):
        """创建 WeatherTool 实例"""
        # 确保设置了 QWEATHER_API_HOST 环境变量
        # 注意：需要在每个测试中设置，因为 _get_api_base_url 每次都会读取环境变量
        original_host = os.environ.get("QWEATHER_API_HOST")
        os.environ["QWEATHER_API_HOST"] = "test-host.re.qweatherapi.com"
        try:
            tool = WeatherTool(jwt_auth=jwt_auth)
            yield tool
        finally:
            # 恢复原始环境变量
            if original_host is not None:
                os.environ["QWEATHER_API_HOST"] = original_host
            elif "QWEATHER_API_HOST" in os.environ:
                del os.environ["QWEATHER_API_HOST"]
    
    def test_init(self, jwt_auth):
        """测试初始化"""
        with patch.dict(os.environ, {"QWEATHER_API_HOST": "test-host.re.qweatherapi.com"}):
            tool = WeatherTool(jwt_auth=jwt_auth)
            assert tool.jwt_auth == jwt_auth
            # 验证 _get_api_base_url 方法返回正确的 URL
            assert tool._get_api_base_url() == "https://test-host.re.qweatherapi.com"
    
    def test_init_missing_api_host(self, jwt_auth):
        """测试缺少 QWEATHER_API_HOST 时初始化失败"""
        with patch.dict(os.environ, {}, clear=True):
            # 移除 QWEATHER_API_HOST
            if "QWEATHER_API_HOST" in os.environ:
                del os.environ["QWEATHER_API_HOST"]
            
            with pytest.raises(WeatherToolError, match="QWEATHER_API_HOST"):
                WeatherTool(jwt_auth=jwt_auth)
    
    def test_search_city_success(self, weather_tool):
        """测试搜索城市成功"""
        # Mock HTTP 请求
        mock_response = {
            "code": "200",
            "location": [
                {
                    "name": "北京",
                    "id": "101010100",
                    "adm1": "北京",
                    "adm2": "北京",
                    "country": "中国"
                }
            ]
        }
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            result = weather_tool.search_city("北京")
            assert result["code"] == "200"
            assert len(result["location"]) > 0
            assert result["location"][0]["name"] == "北京"
            assert result["location"][0]["id"] == "101010100"
    
    def test_search_city_not_found(self, weather_tool):
        """测试搜索城市未找到"""
        mock_response = {
            "code": "404",
            "location": []
        }
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            with pytest.raises(WeatherToolError, match="City.*not found"):
                weather_tool.search_city("不存在的城市")
    
    def test_resolve_location(self, weather_tool):
        """测试解析城市名称到城市ID"""
        mock_response = {
            "code": "200",
            "location": [
                {
                    "name": "上海",
                    "id": "101020100"
                }
            ]
        }
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            city_id = weather_tool._resolve_location("上海")
            assert city_id == "101020100"
    
    def test_get_current_weather_success(self, weather_tool):
        """测试获取实时天气成功"""
        # Mock 城市搜索
        search_response = {
            "code": "200",
            "location": [{"name": "北京", "id": "101010100"}]
        }
        
        # Mock 天气查询
        weather_response = {
            "code": "200",
            "now": {
                "temp": "20",
                "text": "晴",
                "windDir": "北风",
                "windScale": "3"
            }
        }
        
        with patch('httpx.get') as mock_get:
            # 第一次调用：城市搜索
            # 第二次调用：天气查询
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = [search_response, weather_response]
            
            result = weather_tool.get_current_weather("北京")
            assert result["code"] == "200"
            assert "now" in result
            assert result["now"]["temp"] == "20"
    
    def test_get_forecast_success(self, weather_tool):
        """测试获取天气预报成功"""
        # Mock 城市搜索
        search_response = {
            "code": "200",
            "location": [{"name": "北京", "id": "101010100"}]
        }
        
        # Mock 天气预报
        forecast_response = {
            "code": "200",
            "daily": [
                {"date": "2024-01-01", "tempMax": "25", "tempMin": "15"},
                {"date": "2024-01-02", "tempMax": "26", "tempMin": "16"}
            ]
        }
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = [search_response, forecast_response]
            
            result = weather_tool.get_forecast("北京", days=2)
            assert result["code"] == "200"
            assert "daily" in result
            assert len(result["daily"]) == 2
    
    def test_get_warning_success(self, weather_tool):
        """测试获取天气预警成功"""
        # Mock 城市搜索
        search_response = {
            "code": "200",
            "location": [{"name": "北京", "id": "101010100"}]
        }
        
        # Mock 天气预警
        warning_response = {
            "code": "200",
            "warning": [
                {
                    "title": "高温预警",
                    "text": "预计今天最高气温将达到35度"
                }
            ]
        }
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = [search_response, warning_response]
            
            result = weather_tool.get_warning("北京")
            assert result["code"] == "200"
            assert "warning" in result
            assert len(result["warning"]) > 0
    
    def test_make_request_with_jwt_auth(self, weather_tool):
        """测试 API 请求包含 JWT 认证头"""
        mock_response = {"code": "200", "data": "test"}
        
        with patch('httpx.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            weather_tool._make_request("/test", {})
            
            # 验证请求头包含 Authorization
            call_args = mock_get.call_args
            assert "headers" in call_args.kwargs
            assert "Authorization" in call_args.kwargs["headers"]
            assert call_args.kwargs["headers"]["Authorization"].startswith("Bearer ")
    
    def test_make_request_api_error(self, weather_tool):
        """测试 API 请求错误处理"""
        with patch('httpx.get') as mock_get:
            from httpx import HTTPStatusError, Response, Request
            mock_response = Mock(spec=Response)
            mock_response.status_code = 500
            mock_request = Mock(spec=Request)
            
            # 让 raise_for_status 抛出 HTTPStatusError
            def raise_status_error():
                raise HTTPStatusError(
                    "Server Error",
                    request=mock_request,
                    response=mock_response
                )
            
            mock_response.raise_for_status = raise_status_error
            mock_get.return_value = mock_response
            
            with pytest.raises(WeatherToolError, match="API request failed"):
                weather_tool._make_request("/test", {})
    
    def test_make_request_network_error(self, weather_tool):
        """测试网络错误处理"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            with pytest.raises(WeatherToolError, match="Network error"):
                weather_tool._make_request("/test", {})

    def test_make_request_read_timeout(self, weather_tool):
        """复现并验证 read timeout 被正确包装为 WeatherToolError（用户报错：The read operation timed out）"""
        import httpx
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.ReadTimeout("The read operation timed out")
            with pytest.raises(WeatherToolError) as exc_info:
                weather_tool._make_request("/test", {})
            assert "read" in exc_info.value.args[0].lower() or "timed out" in exc_info.value.args[0].lower()
            assert "Network error" in exc_info.value.args[0]

    def test_make_request_connect_timeout(self, weather_tool):
        """复现并验证 connect/SSL handshake timeout 被正确包装"""
        import httpx
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.ConnectTimeout("The handshake operation timed out")
            with pytest.raises(WeatherToolError) as exc_info:
                weather_tool._make_request("/test", {})
            assert "Network error" in exc_info.value.args[0]

