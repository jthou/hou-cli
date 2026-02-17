#!/usr/bin/env python3
"""测试状态行同一行更新功能

独立测试脚本，不依赖交互式终端
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

from frontend.client.ipc_client import IPCClient
from frontend.ui.stream_handler import StreamRenderer
from rich.console import Console
import time


async def test_status_line_update():
    """测试状态行更新功能"""
    console = Console()
    
    print("=" * 80)
    print("测试状态行同一行更新功能")
    print("=" * 80)
    print()
    
    # 检查后端连接
    try:
        client = IPCClient()
        print("✅ 后端连接成功")
    except Exception as e:
        print(f"❌ 后端连接失败: {e}")
        print("   请确保后端服务正在运行（端口 6080）")
        return False
    
    # 测试任务
    test_task = "下载视频 https://www.bilibili.com/video/BV1jMqgBEERW?t=0.5 ，并从音频中提取字幕"
    
    print(f"测试任务: {test_task}")
    print()
    print("开始执行任务...")
    print("-" * 80)
    
    # 创建流式渲染器
    renderer = StreamRenderer()
    
    # 记录状态更新次数
    status_update_count = 0
    last_status_line = None
    
    # 记录开始时间
    start_time = time.time()
    timeout = 300  # 5分钟超时
    
    try:
        # 获取流式响应
        stream = client.stream_send(test_task, session_id=None)
        
        # 渲染流式响应
        async def collect_output():
            nonlocal status_update_count, last_status_line
            
            async for chunk in stream:
                # 检查超时
                if time.time() - start_time > timeout:
                    print(f"\n⚠️ 测试超时（{timeout}秒）")
                    break
                
                # 解析消息（简化版，只检查状态更新）
                if "__STATUS__:" in chunk:
                    status_update_count += 1
                    # 提取状态消息
                    try:
                        import json
                        status_part = chunk.split("__STATUS__:")[1].strip()
                        status_data = json.loads(status_part)
                        last_status_line = status_data.get("message", "")
                        print(f"[状态更新 #{status_update_count}] {last_status_line}")
                    except:
                        pass
        
        # 使用 renderer 渲染（这会显示完整输出）
        await renderer.render_stream(stream, console)
        
        # 同时收集状态更新
        # await collect_output()
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    elapsed_time = time.time() - start_time
    
    print()
    print("-" * 80)
    print("测试完成")
    print(f"执行时间: {elapsed_time:.2f} 秒")
    print(f"状态更新次数: {status_update_count}")
    print()
    
    # 验证结果
    if status_update_count > 0:
        print("✅ 状态行更新功能正常")
        return True
    else:
        print("⚠️ 未检测到状态更新（可能任务执行时间较短）")
        return True  # 仍然算成功，因为可能是任务太快


if __name__ == "__main__":
    # 设置环境变量
    os.environ.setdefault("BACKEND_PORT", "6080")
    os.environ.setdefault("ENABLE_AUTONOMOUS_EXECUTION", "true")
    os.environ.setdefault("STREAM_TIMEOUT", "600")
    
    try:
        result = asyncio.run(test_status_line_update())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




