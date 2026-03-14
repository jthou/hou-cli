#!/usr/bin/env python3
"""测试浏览器自动化功能 - 完整流程测试"""

import asyncio
import os
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "externals" / "browser-use"))
from shared.load_env import load_env
load_env(project_root)

async def test_browser_automation():
    """测试完整的浏览器自动化流程"""
    print("=" * 60)
    print("开始测试浏览器自动化功能")
    print("=" * 60)
    
    # 检查 API Key
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key or api_key == 'your_deepseek_api_key_here':
        print("❌ DEEPSEEK_API_KEY 未设置，请在 .env 文件中配置")
        return
    
    print(f"✅ DEEPSEEK_API_KEY 已设置（长度: {len(api_key)}）")
    
    try:
        # 导入 browser-use 模块
        from browser_use import Agent, Browser, BrowserProfile
        from browser_use.llm.deepseek.chat import ChatDeepSeek
        
        print("\n1. 创建 DeepSeek LLM...")
        llm = ChatDeepSeek(model='deepseek-chat', api_key=api_key)
        print(f"   ✅ LLM 创建成功: {llm.model} ({llm.provider})")
        
        print("\n2. 创建浏览器配置（可见模式）...")
        browser_profile = BrowserProfile(
            headless=False,  # 可见模式
            keep_alive=True,  # 保持浏览器打开以便观察
            # 增加页面加载等待时间，避免页面未完全加载
            minimum_wait_page_load_time=2.0,
            wait_for_network_idle_page_load_time=5.0,
        )
        print("   ✅ 浏览器配置创建成功")
        
        print("\n3. 创建浏览器实例...")
        browser = Browser(browser_profile=browser_profile)
        print("   ✅ 浏览器实例创建成功")
        
        print("\n4. 创建 Agent...")
        # 构建详细的任务描述
        task = """
请执行以下步骤：
1. 打开 www.baidu.com
2. 获取当前页面的 DOM 信息并打印出来
3. 在搜索框中输入 "Browser-use"
4. 点击搜索按钮
5. 等待页面跳转到搜索结果页面
6. 点击搜索结果的第一个链接
7. 等待页面加载完成
8. 获取整个页面的信息（包括标题、URL、主要内容）
9. 打印获取到的页面信息
10. 关闭浏览器

请在每个步骤完成后，打印出当前的状态信息。
"""
        
        agent = Agent(
            task=task,
            llm=llm,
            browser_profile=browser_profile,
            use_vision=False,  # 不使用视觉模式，使用 DOM 信息
            max_steps=20,  # 增加最大步数以确保完成任务
        )
        print("   ✅ Agent 创建成功")
        
        print("\n5. 开始执行任务...")
        print("   任务描述:", task.strip()[:100] + "...")
        print("\n" + "=" * 60)
        print("开始执行浏览器自动化任务...")
        print("=" * 60 + "\n")
        print("注意：浏览器将在可见模式下运行，你可以观察执行过程")
        print("\n" + "=" * 60)
        print("Agent.run() 会等待任务完成，无需额外等待")
        print("browser-use 使用事件驱动架构：")
        print("  - NavigationCompleteEvent 通知页面加载完成")
        print("  - CDP lifecycle events (load, networkIdle) 检测页面状态")
        print("  - 无需 sleep，await 会正确等待")
        print("=" * 60 + "\n")
        
        # 执行任务 - agent.run() 是异步的，会等待任务完成才返回
        print("⏳ 等待 Agent 执行任务（异步等待，无需 sleep）...")
        history = await agent.run(max_steps=30)
        print("✅ Agent.run() 已完成，任务执行完毕\n")
        
        print("\n" + "=" * 60)
        print("任务执行完成")
        print("=" * 60)
        
        # 打印执行结果
        print(f"\n执行步数: {len(history.all_results)}")
        print(f"是否成功: {not history.errors()}")
        
        if history.errors():
            print("\n执行过程中的错误:")
            for error in history.errors():
                print(f"  - {error}")
        
        # 打印最后的结果
        if history.all_results:
            print("\n最后的结果:")
            last_result = history.all_results[-1]
            if hasattr(last_result, 'result'):
                print(f"  结果: {last_result.result}")
            if hasattr(last_result, 'action'):
                print(f"  最后动作: {last_result.action}")
        
        # 打印所有步骤的摘要
        print("\n执行步骤摘要:")
        for i, result in enumerate(history.all_results, 1):
            if hasattr(result, 'action'):
                action_str = str(result.action)[:100]
                print(f"  步骤 {i}: {action_str}")
            elif hasattr(result, 'result'):
                result_str = str(result.result)[:100]
                print(f"  步骤 {i}: {result_str}")
        
        # 尝试读取提取的 DOM 信息
        print("\n" + "=" * 60)
        print("查找提取的 DOM 信息文件...")
        print("=" * 60)
        import glob
        dom_files = glob.glob("/tmp/browser_use_agent_*/browseruse_agent_data/extracted_content*.md")
        if dom_files:
            print(f"\n找到 {len(dom_files)} 个 DOM 信息文件:")
            for dom_file in dom_files[:3]:  # 只显示前3个
                print(f"\n文件: {dom_file}")
                try:
                    with open(dom_file, 'r', encoding='utf-8') as f:
                        content = f.read(500)  # 只读取前500字符
                        print(f"内容预览:\n{content}...")
                except Exception as e:
                    print(f"读取失败: {e}")
        else:
            print("未找到 DOM 信息文件")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(test_browser_automation())
    sys.exit(0 if success else 1)

