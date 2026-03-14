"""测试 Browser Tool 的 Qwen2-VL 视觉功能"""
import sys
from pathlib import Path
import asyncio
import os
import importlib.util

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from shared.load_env import load_env
load_env(project_root)


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


async def test_qwen_configuration():
    """测试 Qwen 配置"""
    print("=" * 60)
    print("测试 1: 视觉模型配置检查")
    print("=" * 60)
    
    bailian_api_key = os.environ.get('BAILIAN_API_KEY')
    bailian_base_url = os.getenv('BAILIAN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    vision_model = os.getenv('BROWSER_TOOL_VISION_MODEL', 'qwen-vl-max-2025-08-13')
    use_vision = os.getenv('BROWSER_TOOL_USE_VISION', 'false').lower() == 'true'
    
    print(f"BAILIAN_API_KEY: {'已设置' if bailian_api_key else '未设置'}")
    if bailian_api_key:
        print(f"  - 长度: {len(bailian_api_key)}")
    
    print(f"BAILIAN_BASE_URL: {bailian_base_url}")
    print(f"BROWSER_TOOL_VISION_MODEL: {vision_model}")
    print(f"BROWSER_TOOL_USE_VISION: {use_vision}")
    
    if not bailian_api_key:
        print("\n⚠️  BAILIAN_API_KEY 未设置，视觉功能将不可用")
        print("   请在 .env 文件中设置 BAILIAN_API_KEY")
        return False
    
    print("\n✅ 视觉模型配置检查通过")
    return True


async def test_vision_detection():
    """测试视觉功能检测"""
    print("\n" + "=" * 60)
    print("测试 2: 视觉功能自动检测")
    print("=" * 60)
    
    browser_module = load_browser_tool()
    BrowserTool = browser_module.BrowserTool
    
    tool = BrowserTool()
    
    # 检查是否强制启用视觉功能
    force_vision = os.getenv("BROWSER_TOOL_USE_VISION", "false").lower() == "true"
    if force_vision:
        print("⚠️  BROWSER_TOOL_USE_VISION=true，所有任务都会使用视觉功能")
        print("   测试用例将根据此设置调整期望值")
    
    # 测试用例（根据是否强制启用视觉功能调整期望值）
    base_test_cases = [
        ("打开网页并截图，告诉我页面内容", True),
        ("使用视觉分析页面布局", True),
        ("打开 www.baidu.com 并识别页面元素", True),
        ("打开 www.baidu.com", False),  # 简单导航，不需要视觉
        ("访问 example.com 并查看页面", True),  # 包含"查看页面"，需要视觉
        ("navigate to example.com", False),  # 简单导航，不需要视觉
        ("screenshot and analyze", True),
        ("visual recognition", True),
    ]
    
    # 如果强制启用视觉功能，所有任务都应该返回 True
    if force_vision:
        test_cases = [(task, True) for task, _ in base_test_cases]
        print("\n注意: 由于 BROWSER_TOOL_USE_VISION=true，所有任务期望值都调整为 True")
    else:
        test_cases = base_test_cases
    
    print("\n测试视觉关键词检测:")
    all_passed = True
    for task, expected in test_cases:
        result = tool._needs_vision(task)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"{status} '{task[:40]}...' -> {result} (期望: {expected})")
    
    if all_passed:
        print("\n✅ 所有视觉检测测试通过")
    else:
        print("\n❌ 部分视觉检测测试失败")
        if force_vision:
            print("   提示: 如果 BROWSER_TOOL_USE_VISION=false，部分测试结果可能不同")
    
    return all_passed


async def test_llm_creation():
    """测试 LLM 创建（使用 Qwen）"""
    print("\n" + "=" * 60)
    print("测试 3: LLM 创建（Qwen2-VL）")
    print("=" * 60)
    
    browser_module = load_browser_tool()
    BrowserTool = browser_module.BrowserTool
    
    tool = BrowserTool()
    
    bailian_api_key = os.environ.get('BAILIAN_API_KEY')
    if not bailian_api_key:
        print("⚠️  BAILIAN_API_KEY 未设置，跳过此测试")
        return False
    
    try:
        # 测试创建 Qwen LLM
        print("创建 Qwen2-VL LLM 实例...")
        llm = tool._create_llm(use_vision=True)
        
        print("✅ Qwen2-VL LLM 创建成功")
        print(f"   - provider: {getattr(llm, 'provider', 'N/A')}")
        print(f"   - model_name: {getattr(llm, 'model_name', 'N/A')}")
        print(f"   - name: {getattr(llm, 'name', 'N/A')}")
        print(f"   - 有 ainvoke: {hasattr(llm, 'ainvoke')}")
        
        # 验证模型名称
        model_name = getattr(llm, 'model_name', '')
        if 'qwen' in model_name.lower() or 'vl' in model_name.lower():
            print(f"✅ 确认使用 Qwen 模型: {model_name}")
            return True
        else:
            print(f"⚠️  模型名称可能不正确: {model_name}")
            return False
            
    except Exception as e:
        print(f"❌ LLM 创建失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_browser_task_with_vision():
    """测试带视觉功能的浏览器任务"""
    print("\n" + "=" * 60)
    print("测试 4: 浏览器任务执行（使用 Qwen2-VL）")
    print("=" * 60)
    
    browser_module = load_browser_tool()
    BrowserTool = browser_module.BrowserTool
    
    bailian_api_key = os.environ.get('BAILIAN_API_KEY')
    if not bailian_api_key:
        print("⚠️  BAILIAN_API_KEY 未设置，跳过此测试")
        return False
    
    tool = BrowserTool()
    
    # 测试任务：包含视觉关键词
    task = "打开 www.baidu.com 并查看页面"
    
    print(f"任务: {task}")
    print("预期: 应该使用 Qwen2-VL 模型（因为包含'查看页面'关键词）")
    print("\n⚠️  这将实际打开浏览器，请观察浏览器窗口")
    print("   如果看到浏览器打开并访问百度，说明配置正确")
    print()
    
    try:
        result = await tool._execute_async(
            task=task,
            headless=False,  # 显示浏览器窗口
            timeout=60
        )
        
        print("\n" + "=" * 60)
        print("执行结果")
        print("=" * 60)
        print(f"成功: {result.success}")
        
        if result.success:
            print(f"消息: {result.data.get('message', 'N/A')}")
            
            # 检查是否使用了 Qwen
            result_text = str(result.data.get('result', ''))
            if 'qwen' in result_text.lower() or 'vl' in result_text.lower():
                print("✅ 检测到 Qwen 模型使用痕迹")
            else:
                print("⚠️  未检测到 Qwen 模型使用痕迹（可能正常，取决于日志）")
            
            # 检查日志中是否有 Qwen 相关信息
            print("\n提示: 请检查日志中是否有 'Qwen2-VL' 或 '使用 Qwen2-VL 模型' 的信息")
        else:
            print(f"错误: {result.error}")
        
        return result.success
        
    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("Browser Tool Qwen2-VL 视觉功能测试")
    print("=" * 60)
    print()
    
    results = []
    
    # 测试 1: 配置检查
    config_ok = await test_qwen_configuration()
    results.append(("配置检查", config_ok))
    
    if not config_ok:
        print("\n⚠️  配置检查失败，部分测试将跳过")
        print("   请先配置 BAILIAN_API_KEY")
    
    # 测试 2: 视觉检测
    detection_ok = await test_vision_detection()
    results.append(("视觉检测", detection_ok))
    
    # 测试 3: LLM 创建
    if config_ok:
        llm_ok = await test_llm_creation()
        results.append(("LLM 创建", llm_ok))
    else:
        results.append(("LLM 创建", None))
    
    # 测试 4: 实际任务执行（可选）
    # 通过环境变量控制是否执行实际浏览器测试
    run_browser_test = os.getenv("TEST_BROWSER_QWEN", "false").lower() == "true"
    
    if config_ok and run_browser_test:
        print("\n" + "=" * 60)
        print("执行实际浏览器任务测试（TEST_BROWSER_QWEN=true）")
        print("=" * 60)
        print("这将实际打开浏览器并访问网站")
        print()
        
        try:
            task_ok = await test_browser_task_with_vision()
            results.append(("浏览器任务", task_ok))
        except Exception as e:
            print(f"\n❌ 浏览器任务测试失败: {str(e)}")
            results.append(("浏览器任务", False))
    elif config_ok:
        print("\n" + "=" * 60)
        print("跳过实际浏览器任务测试")
        print("=" * 60)
        print("要执行实际浏览器测试，请设置环境变量: TEST_BROWSER_QWEN=true")
        print("例如: TEST_BROWSER_QWEN=true python tests/test_browser_qwen_vision.py")
        results.append(("浏览器任务", None))
    else:
        results.append(("浏览器任务", None))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for test_name, result in results:
        if result is None:
            status = "⏭️  跳过"
        elif result:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, r in results if r is True)
    total = sum(1 for _, r in results if r is not None)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total and total > 0:
        print("\n✅ 所有测试通过！Qwen2-VL 视觉功能配置正确")
    elif total == 0:
        print("\n⚠️  没有执行任何测试（配置未完成）")
    else:
        print("\n⚠️  部分测试失败，请检查配置和日志")


if __name__ == "__main__":
    asyncio.run(main())

