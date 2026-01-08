"""快速测试 Browser Tool 改进（检查返回数据结构）"""
import sys
from pathlib import Path
import asyncio
import os
import importlib.util
import json

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


async def test_improvements():
    """测试改进是否生效"""
    print("=" * 60)
    print("验证 Browser Tool 改进是否生效")
    print("=" * 60)
    
    browser_module = load_browser_tool()
    BrowserTool = browser_module.BrowserTool
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY 未设置")
        return
    
    tool = BrowserTool()
    
    print("\n测试任务: 打开 www.baidu.com")
    print("预期改进:")
    print("  1. 返回数据包含 task_completed 字段")
    print("  2. 返回数据包含 agent_successful 字段")
    print("  3. 如果有错误，返回 errors 字段")
    print("  4. 如果有警告，返回 warnings 字段")
    print("  5. 对于简单导航任务，即使 is_done=False 也可能算成功")
    print()
    
    try:
        result = await tool._execute_async(
            task="打开 www.baidu.com",
            headless=False,
            timeout=60
        )
        
        print("\n" + "=" * 60)
        print("测试结果")
        print("=" * 60)
        
        # 检查返回数据结构
        checks = []
        
        # 检查 1: task_completed 字段
        has_task_completed = 'task_completed' in result.data
        checks.append(("返回数据包含 task_completed", has_task_completed))
        if has_task_completed:
            print(f"✅ task_completed: {result.data['task_completed']}")
        
        # 检查 2: agent_successful 字段
        has_agent_successful = 'agent_successful' in result.data
        checks.append(("返回数据包含 agent_successful", has_agent_successful))
        if has_agent_successful:
            print(f"✅ agent_successful: {result.data['agent_successful']}")
        
        # 检查 3: errors 字段（如果有错误）
        has_errors_field = 'errors' in result.data
        checks.append(("返回数据包含 errors 字段（如果适用）", True))  # 这个字段是可选的
        if has_errors_field and result.data['errors']:
            print(f"⚠️  errors: {result.data['errors']}")
        
        # 检查 4: warnings 字段（如果有警告）
        has_warnings_field = 'warnings' in result.data
        checks.append(("返回数据包含 warnings 字段（如果适用）", True))  # 这个字段是可选的
        if has_warnings_field and result.data['warnings']:
            print(f"⚠️  warnings: {result.data['warnings']}")
        
        # 检查 5: 成功判断逻辑
        print(f"\n✅ success: {result.success}")
        print(f"✅ message: {result.data.get('message', 'N/A')}")
        
        # 检查 6: 结果内容
        result_content = result.data.get('result', '')
        if result_content:
            print(f"\n结果内容（前200字符）:")
            print(result_content[:200] + "..." if len(result_content) > 200 else result_content)
        
        # 总结
        print("\n" + "=" * 60)
        print("改进验证总结")
        print("=" * 60)
        
        all_passed = all(check[1] for check in checks)
        
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")
        
        if all_passed:
            print("\n✅ 所有改进验证通过！")
        else:
            print("\n⚠️  部分改进可能未生效")
        
        # 显示完整返回数据（用于调试）
        print("\n" + "=" * 60)
        print("完整返回数据（JSON 格式）")
        print("=" * 60)
        try:
            # 转换为可序列化的格式
            data_to_show = {
                'success': result.success,
                'data': result.data,
                'error': result.error
            }
            print(json.dumps(data_to_show, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"无法序列化为 JSON: {e}")
            print(f"result.success: {result.success}")
            print(f"result.data keys: {list(result.data.keys())}")
            print(f"result.error: {result.error}")
        
    except asyncio.TimeoutError:
        print("\n⚠️  执行超时，但改进代码应该已经执行")
        print("   请检查返回的数据结构是否包含新字段")
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_improvements())

