#!/usr/bin/env python3
"""
实际浏览器功能测试脚本
此脚本用于验证浏览器自动化功能是否能实际运行
"""
import asyncio
import os
from pathlib import Path
import sys
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
from shared.load_env import load_env
load_env(_project_root)

from backend.core.agent.tools.builtin.browser_tool import BrowserTool


def test_actual_browser_functionality():
    """测试实际浏览器功能"""
    print("🔍 开始测试实际浏览器功能...")
    
    # 检查 API 密钥是否设置
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY 未设置，请先配置 .env 文件")
        return False
    
    print("✅ API 密钥已配置")
    
    # 创建浏览器工具实例
    tool = BrowserTool()
    
    # 检查工具健康状态
    is_available, error_msg = tool.check_health()
    if not is_available:
        print(f"❌ 浏览器工具不可用: {error_msg}")
        return False
    
    print("✅ 浏览器工具健康检查通过")
    
    return True


def run_actual_browser_task():
    """运行实际的浏览器任务"""
    if not test_actual_browser_functionality():
        return
    
    print("\n🚀 准备运行浏览器任务...")
    
    # 创建浏览器工具实例
    tool = BrowserTool()
    
    # 定义测试任务
    test_tasks = [
        {
            "task": "打开百度首页并搜索人工智能",
            "headless": False,  # 可视化模式，可以看到浏览器操作
            "timeout": 120
        },
        {
            "task": "打开谷歌搜索人工智能相关文章",
            "headless": False,  # 可视化模式
            "timeout": 120
        }
    ]
    
    for i, task_params in enumerate(test_tasks):
        print(f"\n📋 执行测试任务 {i+1}: {task_params['task']}")
        
        try:
            # 同步执行任务
            result = tool.execute(**task_params)
            print(f"✅ 任务 {i+1} 执行完成")
            print(f"📊 结果: {result.data}")
            
            if result.success:
                print("🎉 任务成功!")
            else:
                print(f"⚠️  任务未成功: {result.data}")
                
        except Exception as e:
            print(f"❌ 任务执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)


async def run_async_browser_task():
    """运行异步浏览器任务"""
    if not test_actual_browser_functionality():
        return
    
    print("\n🚀 准备运行异步浏览器任务...")
    
    # 创建浏览器工具实例
    tool = BrowserTool()
    
    # 定义复杂任务 - 搜索、打开多个网页、提取内容
    complex_task = {
        "task": "搜索人工智能发展趋势，打开前三个搜索结果页面，阅读内容并总结要点",
        "headless": False,  # 可视化模式，可以看到浏览器操作
        "timeout": 180      # 更长的超时时间
    }
    
    print(f"\n📋 执行复杂任务: {complex_task['task']}")
    
    try:
        # 异步执行任务
        result = await tool._execute_async(**complex_task)
        print("✅ 复杂任务执行完成")
        print(f"📊 结果: {result.data}")
        
        if result.success:
            print("🎉 任务成功!")
        else:
            print(f"⚠️  任务未成功: {result.data}")
            
    except Exception as e:
        print(f"❌ 复杂任务执行失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    print("=" * 60)
    print("🔍 浏览器功能实际运行测试")
    print("=" * 60)
    
    # 首先进行健康检查
    if test_actual_browser_functionality():
        print("\n✅ 所有前置检查通过，可以运行实际浏览器任务")
        print("\n💡 提示:")
        print("   - 确保您有有效的 API 密钥")
        print("   - 确保系统已安装 Chrome 浏览器")
        print("   - 确保有适当的系统权限")
        print("   - 在 macOS 上可能需要给予浏览器访问权限")
        
        if len(sys.argv) > 1:
            if sys.argv[1] == "run_sync":
                print("\n🏃‍♂️ 运行同步浏览器任务...")
                run_actual_browser_task()
            elif sys.argv[1] == "run_async":
                print("\n🏃‍♂️ 运行异步浏览器任务...")
                asyncio.run(run_async_browser_task())
            elif sys.argv[1] == "health":
                print("\n✅ 健康检查完成")
            else:
                print("\n📋 可用命令:")
                print("   python test_browser_functionality.py run_sync  # 运行同步测试")
                print("   python test_browser_functionality.py run_async # 运行异步测试")
                print("   python test_browser_functionality.py health    # 仅运行")
        else:
            print("\n📋 您可以运行以下命令来测试实际功能:")
            print("   python test_browser_functionality.py run_sync  # 运行同步测试")
            print("   python test_browser_functionality.py run_async # 运行异步测试")
            print("   python test_browser_functionality.py health    # 仅运行")
    else:
        print("\n❌ 前置检查失败，无法运行实际浏览器任务")
    
    print("=" * 60)