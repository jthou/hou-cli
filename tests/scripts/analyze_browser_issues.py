"""分析 browser-use 执行问题"""
import sys
from pathlib import Path
import asyncio
import os
import importlib.util

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_browser_tool():
    """直接加载 browser_tool 模块"""
    browser_tool_path = project_root / "backend" / "core" / "agent" / "tools" / "builtin" / "browser_tool.py"
    
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


async def analyze_issues():
    """分析问题"""
    print("=" * 60)
    print("Browser-use 执行问题分析")
    print("=" * 60)
    
    browser_module = load_browser_tool()
    BrowserTool = browser_module.BrowserTool
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY 未设置")
        return
    
    tool = BrowserTool()
    
    print("\n问题 1: 页面就绪超时")
    print("-" * 60)
    print("错误信息: Page readiness timeout (4.0s, 4051ms) for https://www.baidu.com")
    print("原因: 页面加载时间超过 4 秒，browser-use 认为页面未就绪")
    print("影响: Agent 可能无法正确识别页面元素")
    print()
    
    print("问题 2: Agent 执行失败")
    print("-" * 60)
    print("错误信息: ❌ Result failed 4/4 times: items")
    print("原因: Agent 尝试执行 'items' 操作（可能是提取页面元素），但失败了")
    print("可能原因:")
    print("  1. 任务描述不够清晰，LLM 返回了错误的操作指令")
    print("  2. 页面元素选择器不正确")
    print("  3. 页面结构变化，Agent 无法找到目标元素")
    print("  4. 页面加载不完整，某些元素还未渲染")
    print()
    
    print("问题 3: 连续失败导致停止")
    print("-" * 60)
    print("错误信息: ❌ Stopping due to 3 consecutive failures")
    print("原因: browser-use 的 Agent 在连续 3 次失败后自动停止")
    print("这是 browser-use 的保护机制，防止无限重试")
    print()
    
    print("=" * 60)
    print("解决方案")
    print("=" * 60)
    
    print("\n方案 1: 使用更简单的任务描述")
    print("-" * 60)
    print("当前任务: '打开 www.baidu.com 并查看页面标题'")
    print("建议改为: '打开 www.baidu.com'")
    print("原因: 更简单的任务描述，减少 Agent 的误判")
    print()
    
    print("方案 2: 增加页面等待时间")
    print("-" * 60)
    print("可以在 Browser 创建时增加等待时间，让页面完全加载")
    print()
    
    print("方案 3: 使用更明确的指令")
    print("-" * 60)
    print("如果确实需要提取信息，使用更明确的指令:")
    print("  '打开 www.baidu.com，等待页面加载完成，然后告诉我页面标题'")
    print()
    
    print("方案 4: 检查浏览器是否实际打开")
    print("-" * 60)
    print("虽然 Agent 执行失败，但浏览器可能已经打开并访问了百度")
    print("这是 browser-use 的一个特性：即使 Agent 失败，浏览器也可能已经执行了部分操作")
    print()
    
    # 测试更简单的任务
    print("\n" + "=" * 60)
    print("测试：使用更简单的任务")
    print("=" * 60)
    
    try:
        result = await tool._execute_async(
            task="打开 www.baidu.com",  # 更简单的任务
            headless=False,
            timeout=60
        )
        
        print(f"\n执行结果:")
        print(f"  成功: {result.success}")
        if result.success:
            print(f"  结果: {str(result.data.get('result', ''))[:200]}...")
        else:
            print(f"  错误: {result.error}")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(analyze_issues())


