#!/usr/bin/env python3
"""
测试浏览器是否能够实际启动
"""

import asyncio
import os
from dotenv import load_dotenv
from browser_use import Agent

# 加载环境变量
load_dotenv()

# 修复环境变量
if not os.getenv('BACKEND_PORT') or os.getenv('BACKEND_PORT') == '':
    os.environ['BACKEND_PORT'] = '6080'


async def test_browser_launch():
    """测试浏览器启动"""
    print("🚀 开始测试浏览器启动...")
    
    try:
        # 创建一个最简单的 agent 来测试浏览器启动
        from backend.services.llm.llm_service import LLMService
        
        llm_service = LLMService()
        llm = llm_service.get_browser_use_llm_with_adaptation(
            model='deepseek-chat'
        )
        
        agent = Agent(
            task='打开百度首页',
            llm=llm,
        )
        
        print("✅ Agent 创建成功")
        
        print("📍 正在执行浏览器任务...")
        
        # 直接运行 agent，让它启动浏览器
        result = await agent.run()
        
        print("🎉 浏览器任务完成！")
        
        print(f"结果: {result}")
        
        print("✅ 浏览器测试完成")
        
    except Exception as e:
        print(f"❌ 浏览器测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_browser_launch())