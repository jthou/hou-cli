"""快速测试 Qwen2-VL 在浏览器任务中的使用"""
import sys
from pathlib import Path
import asyncio
import os
import importlib.util
from dotenv import load_dotenv

# 加载 .env 文件
project_root = Path(__file__).parent.parent
env_file = project_root / '.env'
if env_file.exists():
    load_dotenv(env_file)

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


async def main():
    """快速测试 Qwen2-VL 浏览器任务"""
    print("=" * 60)
    print("Qwen2-VL 浏览器任务快速测试")
    print("=" * 60)
    
    # 检查配置
    qwen_key = os.environ.get('QWEN_API_KEY')
    if not qwen_key:
        print("❌ QWEN_API_KEY 未设置")
        return
    
    print(f"✅ QWEN_API_KEY: 已设置（长度: {len(qwen_key)}）")
    
    browser_module = load_browser_tool()
    BrowserTool = browser_module.BrowserTool
    
    tool = BrowserTool()
    
    # 测试 1: 普通任务（应该使用 DeepSeek）
    print("\n" + "=" * 60)
    print("测试 1: 普通任务（应使用 DeepSeek）")
    print("=" * 60)
    task1 = "打开 www.baidu.com"
    needs_vision1 = tool._needs_vision(task1)
    print(f"任务: {task1}")
    print(f"需要视觉功能: {needs_vision1}")
    print(f"预期模型: {'Qwen2-VL' if needs_vision1 else 'DeepSeek'}")
    
    # 测试 2: 视觉任务（应该使用 Qwen）
    print("\n" + "=" * 60)
    print("测试 2: 视觉任务（应使用 Qwen2-VL）")
    print("=" * 60)
    task2 = "打开 www.baidu.com 并查看页面内容"
    needs_vision2 = tool._needs_vision(task2)
    print(f"任务: {task2}")
    print(f"需要视觉功能: {needs_vision2}")
    print(f"预期模型: {'Qwen2-VL' if needs_vision2 else 'DeepSeek'}")
    
    # 测试 3: 实际执行视觉任务
    if needs_vision2:
        print("\n" + "=" * 60)
        print("测试 3: 执行视觉任务（使用 Qwen2-VL）")
        print("=" * 60)
        print("⚠️  这将实际打开浏览器并使用 Qwen2-VL 模型")
        print("   请观察日志中是否有 '使用 Qwen2-VL 模型' 的信息")
        print()
        
        try:
            result = await tool._execute_async(
                task=task2,
                headless=False,
                timeout=60
            )
            
            print("\n执行结果:")
            print(f"  成功: {result.success}")
            print(f"  消息: {result.data.get('message', 'N/A')}")
            
            # 检查日志中是否有 Qwen 相关信息
            result_text = str(result.data.get('result', ''))
            if 'qwen' in result_text.lower():
                print("  ✅ 检测到 Qwen 模型使用")
            else:
                print("  ⚠️  未在结果中检测到 Qwen（可能正常，取决于日志）")
            
            print("\n提示: 请检查日志输出，应该看到 '使用 Qwen2-VL 模型' 的信息")
            
        except Exception as e:
            print(f"\n❌ 执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

