"""运行 Browser Tool 打开百度（绕过导入问题）"""
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
    """运行 browser tool 打开百度"""
    print("=" * 60)
    print("Browser Tool 实际运行 - 打开百度")
    print("=" * 60)
    
    # 加载模块
    try:
        browser_module = load_browser_tool()
        BrowserTool = browser_module.BrowserTool
        BROWSER_USE_AVAILABLE = browser_module.BROWSER_USE_AVAILABLE
        
        print(f"✅ browser-use 可用: {BROWSER_USE_AVAILABLE}")
    except Exception as e:
        print(f"❌ 加载失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    if not BROWSER_USE_AVAILABLE:
        print("\n❌ browser-use 未安装")
        print("\n安装步骤:")
        print("  1. pip install browser-use langchain-openai playwright")
        print("  2. playwright install chromium")
        print("  3. 确保 DEEPSEEK_API_KEY 已设置")
        return
    
    # 检查 API Key
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("\n❌ DEEPSEEK_API_KEY 未设置")
        print("   请在 .env 文件中设置 DEEPSEEK_API_KEY")
        return
    
    print(f"✅ API Key 已设置（长度: {len(api_key)}）")
    
    # 创建工具实例
    tool = BrowserTool()
    print("✅ BrowserTool 实例创建成功")
    
    # 运行显示模式（headless=False）- 可以看到浏览器
    print("\n" + "=" * 60)
    print("开始运行 Browser Tool")
    print("=" * 60)
    print("任务: 打开 www.baidu.com 并查看页面标题")
    print("模式: 显示浏览器（headless=False）")
    print("⚠️  浏览器窗口将打开，您应该能看到操作过程")
    print()
    
    try:
        result = tool.execute(
            task="打开 www.baidu.com 并查看页面标题",
            headless=False,  # 显示浏览器窗口
            timeout=60
        )
        
        print("\n" + "=" * 60)
        print("执行结果")
        print("=" * 60)
        print(f"成功: {result.success}")
        
        if result.success:
            print(f"\n结果:")
            result_text = result.data.get('result', '')
            print(result_text[:500] if len(result_text) > 500 else result_text)
            print(f"\nheadless: {result.data.get('headless')}")
            print(f"任务: {result.data.get('task')}")
        else:
            print(f"\n错误: {result.error}")
            
    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())


