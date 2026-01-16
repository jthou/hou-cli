"""简单运行 Browser Tool 打开百度"""
import sys
from pathlib import Path
import asyncio
import os
import importlib.util

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_browser_tool():
    """直接加载 browser_tool 模块"""
    browser_tool_path = project_root / "backend" / "core" / "agent" / "tools" / "builtin" / "browser_tool.py"
    
    # 模拟必要的依赖
    class MockTool:
        def __init__(self, name, description, parameters=None):
            self.name = name
            self.description = description
            self.parameters = parameters or []
        
        def validate_parameters(self, **kwargs):
            return None
    
    class MockToolResult:
        def __init__(self, success, data=None, error=None):
            self.success = success
            self.data = data or {}
            self.error = error
    
    class MockToolParameter:
        def __init__(self, name, type, description, required=True, default=None):
            self.name = name
            self.type = type
            self.description = description
            self.required = required
            self.default = default
    
    sys.modules['backend.core.agent.tools.base'] = type(sys)('base')
    sys.modules['backend.core.agent.tools.base'].Tool = MockTool
    sys.modules['backend.core.agent.tools.base'].ToolResult = MockToolResult
    sys.modules['backend.core.agent.tools.base'].ToolParameter = MockToolParameter
    
    spec = importlib.util.spec_from_file_location("browser_tool", browser_tool_path)
    browser_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(browser_module)
    
    return browser_module


async def main():
    """运行 browser tool"""
    print("=" * 60)
    print("Browser Tool - 打开百度（显示模式）")
    print("=" * 60)
    
    # 加载模块
    browser_module = load_browser_tool()
    BrowserTool = browser_module.BrowserTool
    BROWSER_USE_AVAILABLE = browser_module.BROWSER_USE_AVAILABLE
    
    if not BROWSER_USE_AVAILABLE:
        print("❌ browser-use 未安装")
        return
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY 未设置")
        return
    
    print("✅ 环境检查通过")
    print("\n开始运行...")
    print("⚠️  浏览器窗口将打开，您应该能看到浏览器访问 www.baidu.com")
    print()
    
    tool = BrowserTool()
    
    try:
        # 使用较短的超时时间，快速测试
        result = await tool._execute_async(
            task="打开 www.baidu.com",
            headless=False,  # 显示浏览器
            timeout=120  # 增加超时时间
        )
        
        print("\n" + "=" * 60)
        print("执行结果")
        print("=" * 60)
        print(f"成功: {result.success}")
        
        if result.success:
            print(f"\n结果: {result.data.get('result', '')[:300]}")
        else:
            print(f"\n错误: {result.error}")
            
    except asyncio.TimeoutError:
        print("\n⚠️  执行超时，但浏览器可能已经打开")
        print("   请检查是否有浏览器窗口打开并访问了 www.baidu.com")
    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())


