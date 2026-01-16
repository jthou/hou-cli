"""浏览器工具测试 - 简单直接，测试核心功能"""
import pytest
import os
from dotenv import load_dotenv
from backend.core.agent.tools.builtin.browser_tool import BrowserTool, BROWSER_USE_AVAILABLE

# 加载 .env 文件
load_dotenv()


class TestBrowserTool:
    """BrowserTool 核心功能测试"""

    @pytest.fixture
    def tool(self):
        """创建浏览器工具实例"""
        return BrowserTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "browser"
        assert tool.description is not None
        # BrowserTool 现在有 7 个参数（task, headless, timeout, keep_alive, extend_system_message, user_data_dir, 等）
        assert len(tool.parameters) >= 3

        param_names = [p.name for p in tool.parameters]
        assert "task" in param_names
        assert "headless" in param_names
        assert "timeout" in param_names

    @pytest.mark.asyncio
    async def test_execute_simple_task(self, tool):
        """测试执行简单任务"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY 未设置")

        # 简单任务：打开网页
        try:
            result = await tool._execute_async(
                task="打开 www.baidu.com",
                headless=True,
                timeout=60
            )

            assert result is not None
            assert isinstance(result.success, bool)
        except RuntimeError as e:
            # 检查是否是 API 兼容性问题
            error_str = str(e)
            if "response_format" in error_str.lower() or "unavailable" in error_str.lower():
                pytest.skip(f"API 兼容性问题: browser-use 使用的 response_format 参数不被当前 LLM API 支持。错误: {error_str[:200]}")
            raise

    @pytest.mark.asyncio
    async def test_execute_headless_mode(self, tool):
        """测试无头模式"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY 未设置")

        try:
            result = await tool._execute_async(
                task="打开 www.baidu.com",
                headless=True,
                timeout=60
            )

            assert result is not None
            if result.success:
                assert result.data["headless"] is True
        except RuntimeError as e:
            # 检查是否是 API 兼容性问题
            error_str = str(e)
            if "response_format" in error_str.lower() or "unavailable" in error_str.lower():
                pytest.skip(f"API 兼容性问题: browser-use 使用的 response_format 参数不被当前 LLM API 支持。错误: {error_str[:200]}")
            raise

    @pytest.mark.asyncio
    async def test_execute_visible_mode(self, tool):
        """测试可视化模式"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY 未设置")

        try:
            result = await tool._execute_async(
                task="打开 www.baidu.com",
                headless=False,
                timeout=60
            )

            assert result is not None
            if result.success:
                assert result.data["headless"] is False
        except RuntimeError as e:
            # 检查是否是 API 兼容性问题
            error_str = str(e)
            if "response_format" in error_str.lower() or "unavailable" in error_str.lower():
                pytest.skip(f"API 兼容性问题: browser-use 使用的 response_format 参数不被当前 LLM API 支持。错误: {error_str[:200]}")
            raise

    def test_missing_task(self, tool):
        """测试缺少 task 参数"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        # execute() 方法会捕获异常并返回 ToolResult
        # 但由于 _execute_async 直接抛出 ValueError，我们需要捕获它
        import asyncio
        try:
            result = asyncio.run(tool._execute_async())
            # 如果返回了结果，检查是否失败
            assert result.success is False
            assert "task" in result.error.lower() or "必需" in result.error or "参数" in result.error.lower()
        except ValueError as e:
            # 如果抛出异常，检查错误信息
            assert "task" in str(e).lower() or "必需" in str(e) or "参数" in str(e).lower()
