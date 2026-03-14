#!/usr/bin/env python3
"""测试浏览器自动化功能 - 无头模式，获取搜索结果内容"""

import asyncio
import os
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "externals" / "browser-use"))
from shared.load_env import load_env
load_env(project_root)

async def test_browser_headless():
    """测试无头模式的浏览器自动化"""
    print("=" * 60)
    print("开始测试浏览器自动化功能（无头模式）")
    print("=" * 60)
    
    # 检查 API Key
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key or api_key == 'your_deepseek_api_key_here':
        print("❌ DEEPSEEK_API_KEY 未设置，请在 .env 文件中配置")
        return False
    
    print(f"✅ DEEPSEEK_API_KEY 已设置（长度: {len(api_key)}）")
    
    try:
        # 导入 browser-use 模块
        from browser_use import Agent, Browser, BrowserProfile
        from browser_use.llm.deepseek.chat import ChatDeepSeek
        
        print("\n1. 创建 DeepSeek LLM...")
        llm = ChatDeepSeek(model='deepseek-chat', api_key=api_key)
        print(f"   ✅ LLM 创建成功: {llm.model} ({llm.provider})")
        
        print("\n2. 创建浏览器配置（无头模式）...")
        browser_profile = BrowserProfile(
            headless=True,  # 无头模式
            keep_alive=False,  # 任务完成后关闭浏览器
        )
        print("   ✅ 浏览器配置创建成功（headless=True）")
        
        print("\n3. 创建浏览器实例...")
        browser = Browser(browser_profile=browser_profile)
        print("   ✅ 浏览器实例创建成功")
        
        print("\n4. 创建 Agent...")
        # 构建详细的任务描述
        task = """
请执行以下步骤：
1. 打开 www.baidu.com
2. 在搜索框中输入 "browser-use"
3. 点击搜索按钮
4. 等待页面跳转到搜索结果页面
5. 获取排名前三的搜索结果链接的URL和标题
6. 依次点击这三个链接，获取每个页面的完整内容
7. 对于每个页面，提取以下信息：
   - 页面标题
   - 页面URL
   - 页面主要内容（文本内容）
   - 关键信息摘要
8. 将所有三个页面的信息整理并打印出来

请确保：
- 每个步骤完成后等待页面加载完成
- 获取完整的页面内容，不要遗漏重要信息
- 清晰地标识每个页面的信息
"""
        
        agent = Agent(
            task=task,
            llm=llm,
            browser_profile=browser_profile,
            use_vision=False,  # 不使用视觉模式，使用 DOM 信息
            max_steps=50,  # 增加最大步数以确保完成任务
            # step_timeout 保持默认 120 秒
            # 注意：页面加载超时是 4 秒（_navigate_and_wait），这个很合理
            # step_timeout 是整个步骤的超时，包括 extract 操作（可能很慢）
        )
        print("   ✅ Agent 创建成功")
        
        print("\n5. 开始执行任务...")
        print("   任务: 百度搜索 'browser-use' 并获取前三个搜索结果的内容")
        print("\n" + "=" * 60)
        print("开始执行浏览器自动化任务（无头模式）...")
        print("=" * 60 + "\n")
        print("注意：浏览器在无头模式下运行，不会显示窗口")
        print("开始执行...\n")
        print("=" * 60)
        print("Agent.run() 会等待任务完成，无需额外等待")
        print("=" * 60 + "\n")
        
        # 执行任务 - agent.run() 是异步的，会等待任务完成才返回
        # browser-use 内部使用事件驱动架构：
        # - NavigationCompleteEvent 通知页面加载完成
        # - CDP lifecycle events (load, networkIdle) 检测页面状态
        # - Agent 会等待所有步骤完成
        print("⏳ 等待 Agent 执行任务（异步等待，无需 sleep）...")
        history = await agent.run(max_steps=50)
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
                result_str = str(last_result.result)
                # 只显示前500字符
                if len(result_str) > 500:
                    print(f"  结果: {result_str[:500]}...")
                else:
                    print(f"  结果: {result_str}")
            if hasattr(last_result, 'action'):
                print(f"  最后动作: {last_result.action}")
        
        # 打印所有步骤的摘要
        print("\n执行步骤摘要:")
        for i, result in enumerate(history.all_results, 1):
            if hasattr(result, 'action'):
                action_str = str(result.action)[:150]
                print(f"  步骤 {i}: {action_str}")
            elif hasattr(result, 'result'):
                result_str = str(result.result)[:150]
                print(f"  步骤 {i}: {result_str}")
        
        # 尝试读取提取的内容文件
        print("\n" + "=" * 60)
        print("查找提取的内容文件...")
        print("=" * 60)
        import glob
        content_files = glob.glob("/tmp/browser_use_agent_*/browseruse_agent_data/extracted_content*.md")
        if content_files:
            print(f"\n找到 {len(content_files)} 个内容文件:")
            for i, content_file in enumerate(content_files[:5], 1):  # 只显示前5个
                print(f"\n文件 {i}: {content_file}")
                try:
                    with open(content_file, 'r', encoding='utf-8') as f:
                        content = f.read(1000)  # 读取前1000字符
                        print(f"内容预览（前1000字符）:\n{content}...")
                        print(f"\n文件大小: {os.path.getsize(content_file)} 字节")
                except Exception as e:
                    print(f"读取失败: {e}")
        else:
            print("未找到内容文件")
        
        # 查找其他相关文件
        data_dirs = glob.glob("/tmp/browser_use_agent_*/browseruse_agent_data")
        if data_dirs:
            latest_dir = max(data_dirs, key=os.path.getmtime)
            print(f"\n最新数据目录: {latest_dir}")
            all_files = os.listdir(latest_dir)
            print(f"目录中的文件: {', '.join(all_files[:10])}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(test_browser_headless())
    sys.exit(0 if success else 1)

