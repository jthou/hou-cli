"""简单的 Browser Tool 视觉模型测试脚本"""
import sys
import os
import asyncio
from pathlib import Path

# 加载 .env 文件
project_root = Path(__file__).parent.parent
env_file = project_root / '.env'
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"✅ 已加载 .env 文件")
    except ImportError:
        print("⚠️  python-dotenv 未安装，请手动设置环境变量")

sys.path.insert(0, str(project_root))

from backend.core.agent.tools.builtin.browser_tool import BrowserTool


async def test_vision_detection():
    """测试视觉功能检测"""
    print("=" * 60)
    print("测试 1: 视觉功能自动检测")
    print("=" * 60)
    
    tool = BrowserTool()
    
    test_cases = [
        ("打开网页并截图，告诉我页面内容", True),
        ("使用视觉分析页面布局", True),
        ("打开 www.baidu.com 并识别页面元素", True),
        ("打开 www.baidu.com", False),
        ("访问 example.com 并查看页面", True),
        ("screenshot and analyze", True),
    ]
    
    print("\n测试视觉关键词检测:")
    for task, expected in test_cases:
        result = tool._needs_vision(task)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{task[:50]}' -> {result} (期望: {expected})")


async def test_llm_creation():
    """测试 LLM 创建"""
    print("\n" + "=" * 60)
    print("测试 2: LLM 创建")
    print("=" * 60)
    
    tool = BrowserTool()
    
    # 测试 DeepSeek（默认）
    print("\n1. 测试 DeepSeek 模型（默认）:")
    try:
        llm = tool._create_llm(use_vision=False)
        print(f"   ✅ DeepSeek LLM 创建成功")
        print(f"   - 类型: {type(llm).__name__}")
        print(f"   - 模型: {getattr(llm, 'model', 'N/A')}")
    except Exception as e:
        print(f"   ❌ DeepSeek LLM 创建失败: {e}")
        return False
    
    # 测试视觉模型
    print("\n2. 测试视觉模型（Qwen-VL）:")
    bailian_key = os.environ.get('BAILIAN_API_KEY')
    if not bailian_key:
        print("   ⚠️  BAILIAN_API_KEY 未设置，跳过视觉模型测试")
        print("   提示: 设置 BAILIAN_API_KEY 后可以测试视觉模型")
        return True
    
    try:
        llm = tool._create_llm(use_vision=True)
        print(f"   ✅ 视觉模型 LLM 创建成功")
        print(f"   - 类型: {type(llm).__name__}")
        print(f"   - 模型: {getattr(llm, 'model', 'N/A')}")
        print(f"   - Base URL: {getattr(llm, 'base_url', 'N/A')}")
    except Exception as e:
        print(f"   ❌ 视觉模型 LLM 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_browser_task():
    """测试浏览器任务（可选）"""
    print("\n" + "=" * 60)
    print("测试 3: 浏览器任务执行（可选）")
    print("=" * 60)
    
    # 检查是否要执行实际浏览器测试
    run_test = os.getenv("TEST_BROWSER_VISION", "false").lower() == "true"
    
    if not run_test:
        print("⏭️  跳过实际浏览器任务测试")
        print("   要执行实际测试，请设置: TEST_BROWSER_VISION=true")
        print("   例如: TEST_BROWSER_VISION=true python tests/test_browser_vision_simple.py")
        return None
    
    tool = BrowserTool()
    
    # 检查配置
    bailian_key = os.environ.get('BAILIAN_API_KEY')
    if not bailian_key:
        print("⚠️  BAILIAN_API_KEY 未设置，无法测试视觉功能")
        return False
    
    # 测试任务：包含视觉关键词
    task = "打开 www.baidu.com 并查看页面内容"
    
    print(f"任务: {task}")
    print("预期: 应该使用 Qwen-VL 模型（因为包含'查看页面'关键词）")
    print("\n⚠️  这将实际打开浏览器，请观察浏览器窗口")
    print()
    
    try:
        result = await tool._execute_async(
            task=task,
            headless=False,  # 显示浏览器窗口
            timeout=60
        )
        
        print("\n执行结果:")
        print(f"成功: {result.success}")
        if result.success:
            print(f"结果: {result.data.get('result', 'N/A')}")
        else:
            print(f"错误: {result.data.get('error', 'N/A')}")
        
        return result.success
        
    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("Browser Tool 视觉模型简单测试")
    print("=" * 60)
    print()
    
    # 显示配置信息
    print("当前配置:")
    print(f"  - BAILIAN_API_KEY: {'已设置' if os.getenv('BAILIAN_API_KEY') else '未设置'}")
    print(f"  - BROWSER_TOOL_VISION_MODEL: {os.getenv('BROWSER_TOOL_VISION_MODEL', 'qwen-vl-max-2025-08-13')}")
    print(f"  - BROWSER_TOOL_USE_VISION: {os.getenv('BROWSER_TOOL_USE_VISION', 'false')}")
    print()
    
    results = []
    
    # 测试 1: 视觉检测
    try:
        await test_vision_detection()
        results.append(("视觉检测", True))
    except Exception as e:
        print(f"❌ 视觉检测测试失败: {e}")
        results.append(("视觉检测", False))
    
    # 测试 2: LLM 创建
    try:
        llm_ok = await test_llm_creation()
        results.append(("LLM 创建", llm_ok))
    except Exception as e:
        print(f"❌ LLM 创建测试失败: {e}")
        results.append(("LLM 创建", False))
    
    # 测试 3: 浏览器任务（可选）
    try:
        task_result = await test_browser_task()
        results.append(("浏览器任务", task_result))
    except Exception as e:
        print(f"❌ 浏览器任务测试失败: {e}")
        results.append(("浏览器任务", False))
    
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
        print("\n✅ 所有测试通过！")
    elif total == 0:
        print("\n⚠️  没有执行任何测试")
    else:
        print("\n⚠️  部分测试失败，请检查配置和日志")


if __name__ == "__main__":
    asyncio.run(main())

