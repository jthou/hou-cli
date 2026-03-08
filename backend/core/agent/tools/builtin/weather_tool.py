"""天气工具实现"""
import time
import httpx
import os
from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.core.agent.tools.auth.jwt_auth import JWTAuth, JWTAuthError


class WeatherToolError(Exception):
    """天气工具错误"""
    pass


class WeatherTool:
    """天气预报工具"""
    
    def __init__(
        self,
        jwt_auth: JWTAuth
    ):
        """
        初始化天气工具
        
        Args:
            jwt_auth: JWT 认证实例（已包含 kid 和 sub）
        """
        self.jwt_auth = jwt_auth
        
        # 验证 QWEATHER_API_HOST 是否配置
        # 注意：不在这里缓存，每次请求时都从环境变量读取，确保使用最新配置
        api_host = os.getenv("QWEATHER_API_HOST")
        if not api_host:
            raise WeatherToolError(
                "QWEATHER_API_HOST environment variable is required. "
                "Please set it in your .env file (e.g., QWEATHER_API_HOST=m53h2qmd7g.re.qweatherapi.com). "
                "You can find your API Host in the QWeather console under Settings."
            )
        
        # 记录配置信息（用于调试）
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"WeatherTool initialized with QWEATHER_API_HOST: {api_host}")
    
    def _get_api_base_url(self) -> str:
        """
        从环境变量 QWEATHER_API_HOST 构建完整的 API Base URL
        
        Returns:
            完整的 API Base URL（包含协议，例如：https://m53h2qmd7g.re.qweatherapi.com）
            
        Raises:
            WeatherToolError: 如果 QWEATHER_API_HOST 未设置
        """
        api_host = os.getenv("QWEATHER_API_HOST")
        if not api_host:
            raise WeatherToolError(
                "QWEATHER_API_HOST environment variable is required. "
                "Please set it in your .env file (e.g., QWEATHER_API_HOST=m53h2qmd7g.re.qweatherapi.com)."
            )
        
        # 如果 Host 不包含协议，添加 https://
        if not api_host.startswith("http"):
            return f"https://{api_host}"
        else:
            return api_host
    
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
        # 使用 GeoAPI v2 进行城市搜索
        endpoint = f"{self._get_api_base_url()}/geo/v2/city/lookup"
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
        endpoint = f"{self._get_api_base_url()}/v7/weather/now"
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
        endpoint = f"{self._get_api_base_url()}/v7/weather/{days}d"
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
        endpoint = f"{self._get_api_base_url()}/v7/warning/now"
        params = {"location": city_id}
        
        return self._make_request(endpoint, params)
    
    def get_air_quality(self, location: str) -> Dict[str, Any]:
        """
        获取空气质量（AQI）数据
        
        Args:
            location: 城市名称（如：'北京'）
            
        Returns:
            包含空气质量信息的字典，包括AQI、PM2.5、PM10等
        """
        city_id = self._resolve_location(location)
        endpoint = f"{self._get_api_base_url()}/v7/air/now"
        params = {"location": city_id}
        
        return self._make_request(endpoint, params)
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 API 请求（带 JWT 认证）
        
        Args:
            endpoint: API 端点 URL（相对路径或完整 URL）
            params: 请求参数
            
        Returns:
            API 响应数据
            
        Raises:
            WeatherToolError: 如果请求失败
        """
        try:
            # 构建完整的请求 URL
            # 如果 endpoint 已经是完整 URL，直接使用；否则从 QWEATHER_API_HOST 构建完整 URL
            if endpoint.startswith("http://") or endpoint.startswith("https://"):
                full_url = endpoint
            else:
                # 确保 endpoint 以 / 开头
                if not endpoint.startswith("/"):
                    endpoint = "/" + endpoint
                # 从环境变量 QWEATHER_API_HOST 构建完整的 API URL
                full_url = f"{self._get_api_base_url()}{endpoint}"
            
            # 获取 JWT 认证头
            try:
                headers = self.jwt_auth.get_authorization_header()
            except JWTAuthError as jwt_error:
                # JWT 认证错误，提供更详细的错误信息
                raise WeatherToolError(f"JWT authentication failed: {str(jwt_error)}. Please check your JWT configuration (private key, credential ID, project ID).")
            except Exception as jwt_error:
                # 其他 JWT 相关错误
                raise WeatherToolError(f"JWT token generation failed: {str(jwt_error)}. Please check your JWT configuration.")
            
            # 发送请求（连接/读取超时放宽；部分 httpx 版本需提供 default 或全部四参数）
            timeout = httpx.Timeout(35.0, connect=25.0, read=35.0)
            response = httpx.get(full_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            return response.json()
        except WeatherToolError:
            # 重新抛出 WeatherToolError，保持原始错误信息
            raise
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else "unknown"
            error_detail = ""
            try:
                if e.response:
                    error_detail = e.response.text[:200]  # 获取错误详情的前200个字符
            except Exception:
                pass
            msg = f"API request failed with status {status_code}. {error_detail}"
            if status_code == 401:
                msg += (
                    " 和风 401 请检查：1) QWEATHER_API_HOST 是否与控制台项目分配的 Host 一致；"
                    "2) QWEATHER_CREDENTIAL_ID（凭据ID）、QWEATHER_PROJECT_ID（项目ID）是否正确；"
                    "3) WEATHER_JWT_PRIVATE_KEY 是否为 Ed25519 私钥 PEM（与控制台上传的公钥成对）。"
                    "详见和风开发文档：https://dev.qweather.com/docs/configuration/authentication"
                )
            raise WeatherToolError(msg)
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
                    description="城市名称，例如：'北京'、'上海'。未提供时默认北京",
                    required=False
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
            location = (kwargs.get("location") or "").strip()
            if not location:
                location = "北京"
            days = kwargs.get("days", 1)
            
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
            
            # 尝试获取空气质量数据
            air_quality_data = None
            try:
                air_quality_data = self.weather_tool.get_air_quality(location)
            except Exception:
                pass  # 空气质量失败不影响其他数据返回
            
            # 组合返回数据
            result_data = {
                "location": location,
                "current": weather_data.get("now", {}),
                "code": weather_data.get("code", "200")
            }
            
            if air_quality_data and air_quality_data.get("now"):
                result_data["air_quality"] = air_quality_data.get("now", {})
            
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
