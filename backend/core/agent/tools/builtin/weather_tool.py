"""天气工具实现"""
import httpx
import os
from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.core.agent.tools.auth.jwt_auth import JWTAuth


class WeatherToolError(Exception):
    """天气工具错误"""
    pass


class WeatherTool:
    """天气预报工具"""
    
    def __init__(
        self,
        jwt_auth: JWTAuth,
        api_base_url: Optional[str] = None
    ):
        """
        初始化天气工具
        
        Args:
            jwt_auth: JWT 认证实例
            api_base_url: API 基础 URL，如果为 None 则从环境变量读取
        """
        self.jwt_auth = jwt_auth
        self.api_base_url = api_base_url or os.getenv(
            "QWEATHER_API_BASE_URL",
            "https://devapi.qweather.com"
        )
    
    def search_city(self, city_name: str) -> Dict[str, Any]:
        """
        搜索城市，获取城市ID
        
        Args:
            city_name: 城市名称（如：'北京'）
            
        Returns:
            包含城市信息的字典，包括城市ID
            
        Raises:
            WeatherToolError: 如果城市未找到或请求失败
        """
        endpoint = f"{self.api_base_url}/v7/city/lookup"
        params = {"location": city_name}
        
        response = self._make_request(endpoint, params)
        
        if response.get("code") != "200" or not response.get("location"):
            raise WeatherToolError(f"City '{city_name}' not found")
        
        return response
    
    def get_current_weather(self, location: str) -> Dict[str, Any]:
        """
        获取实时天气
        
        Args:
            location: 城市名称（如：'北京'）
            
        Returns:
            包含实时天气信息的字典
        """
        city_id = self._resolve_location(location)
        endpoint = f"{self.api_base_url}/v7/weather/now"
        params = {"location": city_id}
        
        return self._make_request(endpoint, params)
    
    def get_forecast(self, location: str, days: int = 7) -> Dict[str, Any]:
        """
        获取天气预报
        
        Args:
            location: 城市名称（如：'北京'）
            days: 预报天数（1-15）
            
        Returns:
            包含天气预报信息的字典
        """
        if days < 1 or days > 15:
            raise WeatherToolError("Days must be between 1 and 15")
        
        city_id = self._resolve_location(location)
        endpoint = f"{self.api_base_url}/v7/weather/{days}d"
        params = {"location": city_id}
        
        return self._make_request(endpoint, params)
    
    def get_warning(self, location: str) -> Dict[str, Any]:
        """
        获取天气预警
        
        Args:
            location: 城市名称（如：'北京'）
            
        Returns:
            包含天气预警信息的字典
        """
        city_id = self._resolve_location(location)
        endpoint = f"{self.api_base_url}/v7/warning/now"
        params = {"location": city_id}
        
        return self._make_request(endpoint, params)
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 API 请求（带 JWT 认证）
        
        Args:
            endpoint: API 端点 URL
            params: 请求参数
            
        Returns:
            API 响应数据
            
        Raises:
            WeatherToolError: 如果请求失败
        """
        try:
            # 获取 JWT 认证头
            headers = self.jwt_auth.get_authorization_header()
            
            # 发送请求
            response = httpx.get(endpoint, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            return response.json()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else "unknown"
            raise WeatherToolError(f"API request failed: {status_code}")
        except httpx.RequestError as e:
            raise WeatherToolError(f"Network error: {str(e)}")
        except Exception as e:
            raise WeatherToolError(f"Unexpected error: {str(e)}")
    
    def _resolve_location(self, location: str) -> str:
        """
        解析城市名称，返回城市ID
        
        Args:
            location: 城市名称（如：'北京'）
            
        Returns:
            城市ID（如：'101010100'）
            
        Raises:
            WeatherToolError: 城市未找到
        """
        try:
            result = self.search_city(location)
            if result.get("location") and len(result["location"]) > 0:
                return result["location"][0]["id"]
            else:
                raise WeatherToolError(f"City '{location}' not found")
        except WeatherToolError:
            raise
        except Exception as e:
            raise WeatherToolError(f"Failed to resolve location: {str(e)}")


class WeatherToolWrapper(Tool):
    """天气工具包装类（实现 Tool 接口）"""
    
    def __init__(self, weather_tool: WeatherTool):
        """
        初始化天气工具包装
        
        Args:
            weather_tool: WeatherTool 实例
        """
        super().__init__(
            name="get_weather",
            description="获取指定城市的实时天气信息",
            parameters=[
                ToolParameter(
                    name="location",
                    type="string",
                    description="城市名称，例如：'北京'、'上海'。系统会自动将城市名称转换为城市ID",
                    required=True
                ),
                ToolParameter(
                    name="days",
                    type="integer",
                    description="预报天数（1-15），默认1",
                    required=False,
                    default=1
                )
            ]
        )
        self.weather_tool = weather_tool
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行天气查询
        
        Args:
            location: 城市名称
            days: 预报天数（可选，默认1）
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            location = kwargs.get("location")
            days = kwargs.get("days", 1)
            
            if not location:
                return ToolResult(
                    success=False,
                    error="Location parameter is required"
                )
            
            # 获取实时天气
            weather_data = self.weather_tool.get_current_weather(location)
            
            # 如果需要预报，也获取预报数据
            forecast_data = None
            if days > 1:
                try:
                    forecast_data = self.weather_tool.get_forecast(location, days=days)
                except Exception:
                    pass  # 预报失败不影响实时天气返回
            
            # 尝试获取预警
            warning_data = None
            try:
                warning_data = self.weather_tool.get_warning(location)
            except Exception:
                pass  # 预警失败不影响其他数据返回
            
            # 组合返回数据
            result_data = {
                "location": location,
                "current": weather_data.get("now", {}),
                "code": weather_data.get("code", "200")
            }
            
            if forecast_data:
                result_data["forecast"] = forecast_data.get("daily", [])
            
            if warning_data and warning_data.get("warning"):
                result_data["warning"] = warning_data.get("warning", [])
            
            return ToolResult(
                success=True,
                data=result_data
            )
        except WeatherToolError as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )


def get_weather_tool(jwt_auth: JWTAuth) -> Tool:
    """
    创建天气工具实例（Tool 接口）
    
    Args:
        jwt_auth: JWT 认证实例
        
    Returns:
        Tool 实例
    """
    weather_tool = WeatherTool(jwt_auth=jwt_auth)
    return WeatherToolWrapper(weather_tool)
