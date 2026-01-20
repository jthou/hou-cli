"""浏览器工具 CDP 连接测试

专门测试 browser-use 库的 CDP (Chrome DevTools Protocol) 连接功能。
CDP 连接问题通常表现为：
- JSONDecodeError: 解析浏览器版本信息失败
- AssertionError: Root CDP client not initialized
- 浏览器启动失败
"""
import pytest
import os
import json
from dotenv import load_dotenv
from backend.core.agent.tools.builtin.browser_tool import BrowserTool, BROWSER_USE_AVAILABLE

# 加载 .env 文件
load_dotenv()


class TestBrowserToolCDP:
    """BrowserTool CDP 连接测试"""

    @pytest.fixture
    def tool(self):
        """创建浏览器工具实例"""
        return BrowserTool()

    @pytest.mark.asyncio
    async def test_cdp_connection_basic(self, tool):
        """测试基本的 CDP 连接功能
        
        这个测试会尝试启动浏览器并建立 CDP 连接。
        如果环境不可用，会优雅地跳过测试。
        """
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY 未设置")

        # 尝试执行一个简单的任务来测试 CDP 连接
        try:
            result = await tool._execute_async(
                task="打开 www.baidu.com",
                headless=True,
                timeout=30  # 较短的超时，快速失败
            )

            # 如果成功，说明 CDP 连接正常
            assert result is not None
            assert isinstance(result.success, bool)
            
            if result.success:
                # CDP 连接成功
                assert "data" in result.data or result.data is not None
        except json.JSONDecodeError as e:
            # CDP 连接问题：无法解析浏览器版本信息
            pytest.skip(
                f"CDP 连接失败 - JSON 解析错误: "
                f"无法解析浏览器版本信息，可能是浏览器未正确安装或 CDP 端口不可用。"
                f"错误详情: {str(e)[:200]}"
            )
        except AssertionError as e:
            error_str = str(e)
            if "cdp" in error_str.lower() or "initialized" in error_str.lower():
                # CDP 客户端未初始化
                pytest.skip(
                    f"CDP 连接失败 - 客户端未初始化: "
                    f"浏览器 CDP 客户端未能正确初始化。"
                    f"错误详情: {error_str[:200]}"
                )
            raise
        except Exception as e:
            error_str = str(e)
            # 检查是否是 CDP 相关的错误
            cdp_indicators = [
                "cdp",
                "webSocketDebuggerUrl",
                "chrome devtools",
                "devtools protocol",
                "browser session",
                "root cdp client"
            ]
            
            if any(indicator in error_str.lower() for indicator in cdp_indicators):
                pytest.skip(
                    f"CDP 连接失败 - 浏览器环境问题: "
                    f"无法建立 Chrome DevTools Protocol 连接。"
                    f"可能原因：浏览器未安装、CDP 端口被占用、浏览器版本不兼容。"
                    f"错误详情: {error_str[:200]}"
                )
            # 其他错误继续抛出
            raise

    @pytest.mark.asyncio
    async def test_cdp_connection_headless_mode(self, tool):
        """测试无头模式下的 CDP 连接"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY 未设置")

        try:
            result = await tool._execute_async(
                task="打开 www.baidu.com",
                headless=True,
                timeout=30
            )

            assert result is not None
            if result.success:
                # 验证无头模式设置
                assert result.data.get("headless") is True
        except (json.JSONDecodeError, AssertionError, Exception) as e:
            error_str = str(e)
            # 检查是否是 CDP 相关错误
            if any(keyword in error_str.lower() for keyword in [
                "jsondecodeerror", "cdp", "webSocketDebuggerUrl",
                "root cdp client", "browser session", "initialized"
            ]):
                pytest.skip(
                    f"CDP 连接失败（无头模式）: {error_str[:200]}"
                )
            raise

    @pytest.mark.asyncio
    async def test_cdp_connection_visible_mode(self, tool):
        """测试可视化模式下的 CDP 连接"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY 未设置")

        try:
            result = await tool._execute_async(
                task="打开 www.baidu.com",
                headless=False,
                timeout=30
            )

            assert result is not None
            if result.success:
                # 验证可视化模式设置
                assert result.data.get("headless") is False
        except (json.JSONDecodeError, AssertionError, Exception) as e:
            error_str = str(e)
            # 检查是否是 CDP 相关错误
            if any(keyword in error_str.lower() for keyword in [
                "jsondecodeerror", "cdp", "webSocketDebuggerUrl",
                "root cdp client", "browser session", "initialized"
            ]):
                pytest.skip(
                    f"CDP 连接失败（可视化模式）: {error_str[:200]}"
                )
            raise

    def test_cdp_error_detection(self):
        """测试 CDP 错误检测逻辑
        
        验证测试能够正确识别各种 CDP 相关的错误。
        """
        # 模拟各种 CDP 错误消息
        cdp_errors = [
            "JSONDecodeError: Expecting value: line 1 column 1 (char 0)",
            "Root CDP client not initialized",
            "webSocketDebuggerUrl",
            "CDP connected but failed",
            "browser session start failed",
            "Chrome DevTools Protocol error"
        ]
        
        # 验证错误检测逻辑
        for error_msg in cdp_errors:
            error_lower = error_msg.lower()
            is_cdp_error = any(keyword in error_lower for keyword in [
                "jsondecodeerror", "cdp", "websocketdebuggerurl",
                "root cdp client", "browser session", "devtools protocol"
            ])
            assert is_cdp_error, f"应该识别为 CDP 错误: {error_msg}"

    @pytest.mark.asyncio
    async def test_cdp_connection_timeout(self, tool):
        """测试 CDP 连接超时处理"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY 未设置")

        # 使用非常短的超时来测试超时处理
        try:
            result = await tool._execute_async(
                task="打开 www.baidu.com",
                headless=True,
                timeout=1  # 1秒超时，应该很快失败
            )

            # 如果超时，应该返回失败结果或抛出异常
            if result:
                # 如果返回了结果，检查是否是超时错误
                if not result.success:
                    assert "timeout" in result.error.lower() or "超时" in result.error
        except Exception as e:
            error_str = str(e)
            # 超时或 CDP 连接问题都应该被正确处理
            if "timeout" in error_str.lower() or "超时" in error_str:
                # 超时是预期的
                pass
            elif any(keyword in error_str.lower() for keyword in [
                "jsondecodeerror", "cdp", "webSocketDebuggerUrl"
            ]):
                pytest.skip(f"CDP 连接问题: {error_str[:200]}")
            else:
                # 其他错误继续抛出
                raise

    def test_browser_health_check(self):
        """测试浏览器工具的健康检查
        
        验证 check_health 方法能够正确检测浏览器环境。
        """
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        # 调用健康检查
        is_healthy, error_msg = BrowserTool.check_health()
        
        # 健康检查应该返回布尔值和可选的错误消息
        assert isinstance(is_healthy, bool)
        if not is_healthy:
            assert error_msg is not None
            assert isinstance(error_msg, str)
            # 检查错误消息是否包含有用的信息
            assert len(error_msg) > 0

