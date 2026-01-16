"""Browser Tool 手动测试脚本"""
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import os
from unittest.mock import Mock, patch, AsyncMock
from backend.core.agent.tools.builtin.browser_tool import BrowserTool, BROWSER_USE_AVAILABLE


def test_tool_initialization():
    """测试工具初始化"""
    print("=" * 60)
    print("测试 1: 工具初始化")
    print("=" * 60)
    
    tool = BrowserTool()
    assert tool.name == "browser"
    assert tool.description is not None
    assert len(tool.parameters) > 0
    
    param_names = [p.name for p in tool.parameters]
    assert "task" in param_names
    assert "headless" in param_names
    assert "timeout" in param_names
    
    print(f"✅ 工具名称: {tool.name}")
    print(f"✅ 工具描述长度: {len(tool.description)}")
    print(f"✅ 参数数量: {len(tool.parameters)}")
    print(f"✅ 参数名称: {param_names}")
    print()


def test_validate_parameters():
    """测试参数验证"""
    print("=" * 60)
    print("测试 2: 参数验证")
    print("=" * 60)
    
    tool = BrowserTool()
    
    # 测试缺少必需参数
    error = tool.validate_parameters()
    assert error is not None
    print(f"✅ 缺少参数时返回错误: {error[:50]}...")
    
    # 测试有效参数
    error = tool.validate_parameters(task="打开 www.baidu.com")
    assert error is None
    print("✅ 有效参数验证通过")
    print()


def test_execute_without_browser_use():
    """测试 browser-use 未安装时的执行"""
    print("=" * 60)
    print("测试 3: browser-use 未安装时的执行")
    print("=" * 60)
    
    import asyncio
    
    with patch('backend.core.agent.tools.builtin.browser_tool.BROWSER_USE_AVAILABLE', False):
        import importlib
        import backend.core.agent.tools.builtin.browser_tool as browser_module
        importlib.reload(browser_module)
        
        tool = browser_module.BrowserTool()
        
        async def run_test():
            result = await tool._execute_async(task="打开 www.baidu.com")
            assert result.success is False
            assert "not installed" in result.error.lower() or "需要安装" in result.error.lower()
            print(f"✅ 正确返回错误: {result.error[:60]}...")
        
        asyncio.run(run_test())
    print()


def test_execute_missing_task():
    """测试缺少 task 参数"""
    print("=" * 60)
    print("测试 4: 缺少 task 参数")
    print("=" * 60)
    
    if not BROWSER_USE_AVAILABLE:
        print("⚠️  browser-use 未安装，跳过测试")
        return
    
    import asyncio
    
    tool = BrowserTool()
    
    async def run_test():
        result = await tool._execute_async()
        assert result.success is False
        assert "task" in result.error.lower() or "required" in result.error.lower()
        print(f"✅ 正确返回错误: {result.error[:60]}...")
    
    asyncio.run(run_test())
    print()


def test_create_llm_missing_api_key():
    """测试缺少 API Key"""
    print("=" * 60)
    print("测试 5: 缺少 API Key")
    print("=" * 60)
    
    if not BROWSER_USE_AVAILABLE:
        print("⚠️  browser-use 未安装，跳过测试")
        return
    
    tool = BrowserTool()
    
    with patch.dict(os.environ, {}, clear=True):
        try:
            tool._create_llm()
            print("❌ 应该抛出 ValueError")
        except ValueError as e:
            assert "DEEPSEEK_API_KEY" in str(e)
            print(f"✅ 正确抛出错误: {str(e)[:60]}...")
    print()


def test_conversation_path():
    """测试对话路径创建"""
    print("=" * 60)
    print("测试 6: 对话路径创建")
    print("=" * 60)
    
    tool = BrowserTool()
    assert tool.conversation_path.exists()
    assert tool.conversation_path.is_dir()
    print(f"✅ 对话路径: {tool.conversation_path}")
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Browser Tool 单元测试（手动运行）")
    print("=" * 60 + "\n")
    
    tests = [
        test_tool_initialization,
        test_validate_parameters,
        test_execute_without_browser_use,
        test_execute_missing_task,
        test_create_llm_missing_api_key,
        test_conversation_path,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            if "跳过" in str(e) or "skip" in str(e).lower():
                skipped += 1
            else:
                failed += 1
                print(f"❌ {test.__name__} 失败: {str(e)}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"⚠️  跳过: {skipped}")
    print(f"📊 总计: {passed + failed + skipped}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

