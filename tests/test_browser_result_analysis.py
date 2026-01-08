"""测试 Browser Tool 的结果分析改进"""
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


async def test_result_analysis():
    """测试结果分析功能"""
    print("=" * 60)
    print("测试 Browser Tool 结果分析改进")
    print("=" * 60)
    
    browser_module = load_browser_tool()
    BrowserTool = browser_module.BrowserTool
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY 未设置")
        return
    
    tool = BrowserTool()
    
    # 测试 1: 简单导航任务
    print("\n" + "=" * 60)
    print("测试 1: 简单导航任务（打开网页）")
    print("=" * 60)
    
    try:
        result = await tool._execute_async(
            task="打开 www.baidu.com",
            headless=False,
            timeout=60
        )
        
        print(f"\n执行结果:")
        print(f"  成功: {result.success}")
        print(f"  任务完成: {result.data.get('task_completed', 'N/A')}")
        print(f"  Agent 成功: {result.data.get('agent_successful', 'N/A')}")
        
        if result.data.get('warnings'):
            print(f"  警告: {result.data.get('warnings')}")
        
        if result.data.get('errors'):
            print(f"  错误: {result.data.get('errors')}")
        
        print(f"\n结果摘要: {result.data.get('message', 'N/A')}")
        print(f"结果内容: {str(result.data.get('result', ''))[:200]}...")
        
        # 验证改进
        print("\n✅ 改进验证:")
        print(f"  - 返回数据包含 task_completed: {'task_completed' in result.data}")
        print(f"  - 返回数据包含 agent_successful: {'agent_successful' in result.data}")
        print(f"  - 成功判断基于实际状态: {result.success == result.data.get('agent_successful', True)}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n改进说明:")
    print("1. ✅ 使用 AgentHistoryList.is_successful 判断任务是否真正成功")
    print("2. ✅ 使用 AgentHistoryList.is_done 判断任务是否完成")
    print("3. ✅ 检查 errors 和 action_results 获取详细错误信息")
    print("4. ✅ 对于简单导航任务，即使 is_done=False 也可能算成功")
    print("5. ✅ 返回详细的状态信息（task_completed, agent_successful, errors, warnings）")


if __name__ == "__main__":
    asyncio.run(test_result_analysis())

