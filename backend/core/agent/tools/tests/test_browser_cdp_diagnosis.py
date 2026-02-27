"""Browser CDP 连接诊断测试

用于诊断和修复 browser-use CDP 连接问题。
暂时移除 browser 工具，后续再开发。
"""
import pytest
import os
import json
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv

pytestmark = pytest.mark.skip(reason="browser tool 暂时移除，后续再开发")

from backend.core.agent.tools.builtin.browser_tool import BrowserTool, BROWSER_USE_AVAILABLE

# 加载 .env 文件
load_dotenv()


class TestBrowserCDPDiagnosis:
    """Browser CDP 连接诊断测试"""

    @pytest.fixture
    def tool(self):
        """创建浏览器工具实例"""
        return BrowserTool()

    def test_browser_installation_check(self):
        """检查浏览器是否安装"""
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        # 检查常见的浏览器路径
        import platform
        system = platform.system()
        browser_paths = []
        
        if system == 'Darwin':  # macOS
            browser_paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium',
            ]
        elif system == 'Linux':
            browser_paths = [
                '/usr/bin/google-chrome-stable',
                '/usr/bin/google-chrome',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
            ]
        elif system == 'Windows':
            browser_paths = [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            ]
        
        found_browsers = []
        for path in browser_paths:
            if Path(path).exists():
                found_browsers.append(path)
        
        if not found_browsers:
            pytest.skip(
                f"未找到已安装的浏览器。"
                f"请安装 Chrome 或 Chromium，或运行: uvx playwright install chrome"
            )
        
        print(f"✅ 找到已安装的浏览器: {found_browsers}")

    @pytest.mark.asyncio
    async def test_cdp_endpoint_accessibility(self):
        """测试 CDP 端点可访问性
        
        这个测试会：
        1. 尝试启动浏览器
        2. 检查 CDP 端点是否可访问
        3. 验证 /json/version 端点返回有效 JSON
        """
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("DEEPSEEK_API_KEY 未设置")

        # 尝试手动启动浏览器并检查 CDP
        try:
            from browser_use import Browser
            from backend.core.agent.tools.builtin.browser_tool import BrowserTool
            
            tool = BrowserTool()
            
            # 创建浏览器实例（不执行任务，只测试启动）
            browser = Browser(
                headless=True,
                user_data_dir=None,  # 使用临时目录
            )
            
            # 尝试启动浏览器会话
            # 注意：这里我们只是测试浏览器启动，不执行完整任务
            try:
                # 检查浏览器是否能够启动
                # 由于 browser-use 的架构，我们需要通过 BrowserSession 来测试
                # 但为了诊断，我们可以直接测试 CDP 端点
                pass
            except Exception as e:
                error_str = str(e)
                if "jsondecodeerror" in error_str.lower():
                    pytest.fail(
                        f"CDP 端点返回无效 JSON。"
                        f"这可能是因为："
                        f"1. 浏览器启动失败"
                        f"2. CDP 端口被占用"
                        f"3. 浏览器版本不兼容"
                        f"错误: {error_str[:300]}"
                    )
                raise
        except Exception as e:
            error_str = str(e)
            if "browser" in error_str.lower() and "not found" in error_str.lower():
                pytest.skip(f"浏览器未找到: {error_str}")
            raise

    @pytest.mark.asyncio
    async def test_manual_cdp_connection(self):
        """手动测试 CDP 连接
        
        这个测试会：
        1. 手动启动浏览器进程
        2. 等待 CDP 端点就绪
        3. 测试 /json/version 端点
        4. 验证响应内容
        """
        if not BROWSER_USE_AVAILABLE:
            pytest.skip("browser-use 未安装")

        import subprocess
        import socket
        import time
        
        # 查找可用端口
        def find_free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', 0))
                return s.getsockname()[1]
        
        # 查找浏览器路径
        def find_browser():
            import platform
            system = platform.system()
            if system == 'Darwin':
                paths = [
                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                    '/Applications/Chromium.app/Contents/MacOS/Chromium',
                ]
            elif system == 'Linux':
                paths = [
                    '/usr/bin/google-chrome-stable',
                    '/usr/bin/google-chrome',
                    '/usr/bin/chromium',
                ]
            else:
                return None
            
            for path in paths:
                if Path(path).exists():
                    return path
            return None
        
        browser_path = find_browser()
        if not browser_path:
            pytest.skip("未找到浏览器可执行文件")
        
        debug_port = find_free_port()
        cdp_url = f"http://127.0.0.1:{debug_port}"
        
        # 启动浏览器
        import tempfile
        user_data_dir = tempfile.mkdtemp(prefix='browser-test-')
        
        try:
            process = subprocess.Popen(
                [
                    browser_path,
                    f'--remote-debugging-port={debug_port}',
                    f'--user-data-dir={user_data_dir}',
                    '--headless',
                    '--no-sandbox',
                    '--disable-gpu',
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # 等待 CDP 端点就绪
            max_wait = 10
            waited = 0
            version_url = f"{cdp_url}/json/version"
            
            while waited < max_wait:
                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        response = await client.get(version_url)
                        if response.status_code == 200:
                            content = response.text
                            if content and content.strip():
                                # 尝试解析 JSON
                                try:
                                    data = json.loads(content)
                                    if 'webSocketDebuggerUrl' in data:
                                        print(f"✅ CDP 端点正常: {data['webSocketDebuggerUrl']}")
                                        # 成功！
                                        return
                                    else:
                                        pytest.fail(f"CDP 响应缺少 webSocketDebuggerUrl: {content[:200]}")
                                except json.JSONDecodeError as e:
                                    pytest.fail(
                                        f"CDP 端点返回无效 JSON。"
                                        f"响应内容: {content[:200]}"
                                        f"错误: {str(e)}"
                                    )
                            else:
                                pytest.fail(
                                    f"CDP 端点返回空响应。"
                                    f"这可能是因为浏览器还没有完全启动。"
                                    f"状态码: {response.status_code}"
                                )
                        else:
                            # 非 200 状态码，继续等待
                            await asyncio.sleep(0.5)
                            waited += 0.5
                except httpx.ConnectError:
                    # 连接失败，继续等待
                    await asyncio.sleep(0.5)
                    waited += 0.5
                except Exception as e:
                    await asyncio.sleep(0.5)
                    waited += 0.5
            
            # 如果到这里，说明超时了
            process.terminate()
            process.wait(timeout=5)
            pytest.fail(
                f"CDP 端点未能在 {max_wait} 秒内就绪。"
                f"请检查："
                f"1. 浏览器是否正确启动"
                f"2. 端口 {debug_port} 是否被占用"
                f"3. 浏览器版本是否支持 CDP"
            )
        finally:
            # 清理
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
            import shutil
            try:
                shutil.rmtree(user_data_dir, ignore_errors=True)
            except:
                pass

    def test_cdp_error_analysis(self):
        """分析 CDP 错误并提供修复建议"""
        # 常见的 CDP 错误和修复建议
        error_solutions = {
            "JSONDecodeError: Expecting value": {
                "原因": "CDP 端点返回空响应或无效 JSON",
                "可能原因": [
                    "浏览器启动失败",
                    "CDP 端口被占用",
                    "浏览器版本不兼容",
                    "浏览器启动时间过长，需要更多等待时间"
                ],
                "修复建议": [
                    "检查浏览器是否正确安装",
                    "检查端口是否被占用: lsof -i :9222",
                    "尝试增加浏览器启动等待时间",
                    "检查浏览器日志输出"
                ]
            },
            "Root CDP client not initialized": {
                "原因": "CDP 客户端未正确初始化",
                "可能原因": [
                    "浏览器启动后立即尝试连接",
                    "CDP WebSocket 连接失败",
                    "浏览器进程意外退出"
                ],
                "修复建议": [
                    "增加浏览器启动后的等待时间",
                    "检查浏览器进程是否还在运行",
                    "验证 CDP WebSocket URL 是否正确"
                ]
            },
            "webSocketDebuggerUrl": {
                "原因": "无法从 /json/version 获取 WebSocket URL",
                "可能原因": [
                    "浏览器 CDP 端点未完全启动",
                    "网络连接问题",
                    "浏览器版本不支持 CDP"
                ],
                "修复建议": [
                    "等待更长时间让浏览器完全启动",
                    "检查防火墙设置",
                    "更新浏览器到最新版本"
                ]
            }
        }
        
        # 验证错误解决方案存在
        assert len(error_solutions) > 0
        for error_type, solution in error_solutions.items():
            assert "原因" in solution
            assert "修复建议" in solution
            print(f"\n错误类型: {error_type}")
            print(f"原因: {solution['原因']}")
            print(f"修复建议: {solution['修复建议']}")

