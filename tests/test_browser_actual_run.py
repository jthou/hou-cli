"""Browser Tool 实际运行测试（打开浏览器）"""
import sys
from pathlib import Path
import asyncio
import os

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_browser_open_baidu():
    """实际运行 browser tool 打开百度"""
    print("=" * 60)
    print("Browser Tool 实际运行测试")
    print("=" * 60)
    
    # 检查依赖
    try:
        from backend.core.agent.tools.builtin.browser_tool import BrowserTool, BROWSER_USE_AVAILABLE
        print(f"✅ browser-use 可用: {BROWSER_USE_AVAILABLE}")
    except Exception as e:
        print(f"❌ 导入失败: {str(e)}")
        return
    
    if not BROWSER_USE_AVAILABLE:
        print("❌ browser-use 未安装，无法运行实际测试")
        print("   安装命令: pip install browser-use langchain-openai playwright")
        print("   然后运行: playwright install chromium")
        return
    
    # 检查 API Key
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY 未设置")
        print("   需要在 .env 文件中设置 DEEPSEEK_API_KEY")
        return
    
    print(f"✅ API Key 已设置（长度: {len(api_key)}）")
    
    # 创建工具实例
    tool = BrowserTool()
    print("✅ BrowserTool 实例创建成功")
    
    # 测试 1: 显示模式（headless=False）- 可以看到浏览器窗口
    print("\n" + "=" * 60)
    print("测试 1: 显示模式打开百度（headless=False）")
    print("=" * 60)
    print("⚠️  这将打开浏览器窗口，您应该能看到浏览器操作过程")
    print("   任务: 打开 www.baidu.com")
    print("   模式: 显示浏览器（headless=False）")
    print()
    
    try:
        result = tool.execute(
            task="打开 www.baidu.com 并查看页面标题",
            headless=False,  # 显示浏览器
            timeout=30
        )
        
        print(f"\n执行结果:")
        print(f"  成功: {result.success}")
        if result.success:
            print(f"  结果: {result.data.get('result', '')[:200]}...")
            print(f"  headless: {result.data.get('headless')}")
        else:
            print(f"  错误: {result.error}")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


async def test_browser_open_baidu_headless():
    """无头模式测试（不显示浏览器）"""
    print("\n" + "=" * 60)
    print("测试 2: 无头模式打开百度（headless=True）")
    print("=" * 60)
    print("⚠️  这将以无头模式运行，不会显示浏览器窗口")
    print("   任务: 打开 www.baidu.com")
    print("   模式: 无头模式（headless=True）")
    print()
    
    try:
        from backend.core.agent.tools.builtin.browser_tool import BrowserTool, BROWSER_USE_AVAILABLE
        
        if not BROWSER_USE_AVAILABLE:
            print("⚠️  browser-use 未安装，跳过测试")
            return
        
        tool = BrowserTool()
        
        result = tool.execute(
            task="打开 www.baidu.com 并提取页面标题",
            headless=True,  # 无头模式
            timeout=30
        )
        
        print(f"\n执行结果:")
        print(f"  成功: {result.success}")
        if result.success:
            print(f"  结果: {result.data.get('result', '')[:200]}...")
            print(f"  headless: {result.data.get('headless')}")
        else:
            print(f"  错误: {result.error}")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """运行测试"""
    print("\n" + "=" * 60)
    print("Browser Tool 实际运行测试")
    print("=" * 60)
    print("\n这将实际打开浏览器并访问 www.baidu.com")
    print("请确保：")
    print("  1. browser-use 已安装")
    print("  2. playwright chromium 已安装")
    print("  3. DEEPSEEK_API_KEY 已设置")
    print()
    
    input("按 Enter 继续，或 Ctrl+C 取消...")
    
    # 先运行显示模式测试（用户可以看到浏览器）
    await test_browser_open_baidu()
    
    # 询问是否运行无头模式测试
    print("\n是否运行无头模式测试？(y/n): ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            await test_browser_open_baidu_headless()
    except KeyboardInterrupt:
        print("\n测试已取消")


if __name__ == "__main__":
    asyncio.run(main())


