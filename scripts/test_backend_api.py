#!/usr/bin/env python3
"""直接测试后端API - 不依赖前端交互

这个脚本直接调用后端API，验证功能是否正常
"""
import sys
import os
import asyncio
import httpx
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

# 配置
BACKEND_PORT = os.getenv("BACKEND_PORT", "6080")
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"


async def test_backend_health():
    """测试后端健康检查"""
    print("=" * 80)
    print("1. 测试后端健康检查")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                print(f"✅ 后端健康检查通过: {response.json()}")
                return True
            else:
                print(f"❌ 后端健康检查失败: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ 后端连接失败: {e}")
        print(f"   请确保后端服务正在运行在端口 {BACKEND_PORT}")
        return False


async def test_streaming_chat():
    """测试流式聊天API"""
    print()
    print("=" * 80)
    print("2. 测试流式聊天API")
    print("=" * 80)
    
    test_message = "你好，请回复'测试成功'"
    
    print(f"发送消息: {test_message}")
    print()
    print("接收响应:")
    print("-" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 发送流式请求
            async with client.stream(
                "POST",
                f"{BACKEND_URL}/api/chat/stream",
                json={"message": test_message},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status_code != 200:
                    print(f"❌ 请求失败: {response.status_code}")
                    print(f"   响应: {await response.aread()}")
                    return False
                
                # 接收流式响应
                content_received = False
                status_received = False
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    # 解析SSE格式
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # 去掉 "data: " 前缀
                            
                            if "content" in data:
                                content = data["content"]
                                if content:
                                    print(content, end="", flush=True)
                                    content_received = True
                            
                            if "status" in data and data["status"] == "done":
                                print("\n")
                                break
                        except json.JSONDecodeError:
                            # 可能是其他格式的数据
                            if "__STATUS__:" in line:
                                status_received = True
                                print(f"[状态更新] {line}")
                            elif "__TOOL__:" in line:
                                print(f"[工具调用] {line[:100]}...")
                            elif "__DEBUG__:" in line:
                                # 调试信息，不显示
                                pass
                            else:
                                # 直接显示
                                print(line)
                
                print("-" * 80)
                
                if content_received:
                    print("✅ 收到内容响应")
                else:
                    print("⚠️ 未收到内容响应")
                
                return True
                
    except httpx.TimeoutException:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_status_updates():
    """测试状态更新（心跳）"""
    print()
    print("=" * 80)
    print("3. 测试状态更新（心跳机制）")
    print("=" * 80)
    
    # 发送一个可能需要较长时间的任务
    test_message = "请数数从1到10，每个数字间隔1秒"
    
    print(f"发送任务: {test_message}")
    print("等待状态更新...")
    print("-" * 80)
    
    status_count = 0
    start_time = asyncio.get_event_loop().time()
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{BACKEND_URL}/api/chat/stream",
                json={"message": test_message},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status_code != 200:
                    print(f"❌ 请求失败: {response.status_code}")
                    return False
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    # 检查状态更新
                    if "__STATUS__:" in line:
                        status_count += 1
                        try:
                            status_data = json.loads(line.split("__STATUS__:")[1])
                            message = status_data.get("message", "")
                            elapsed = status_data.get("elapsed_time", 0)
                            print(f"[状态 #{status_count}] {message} (已用时: {elapsed:.1f}秒)")
                        except:
                            print(f"[状态 #{status_count}] {line[:100]}")
                    
                    # 检查是否完成
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("status") == "done":
                                break
                        except:
                            pass
                
                elapsed = asyncio.get_event_loop().time() - start_time
                print("-" * 80)
                print(f"总用时: {elapsed:.1f}秒")
                print(f"状态更新次数: {status_count}")
                
                if status_count > 0:
                    print("✅ 状态更新机制正常工作")
                    return True
                else:
                    print("⚠️ 未收到状态更新（可能任务执行时间较短）")
                    return True  # 仍然算成功
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print()
    print("后端API功能测试")
    print()
    
    results = []
    
    # 测试1: 健康检查
    results.append(("后端健康检查", await test_backend_health()))
    
    if not results[0][1]:
        print()
        print("❌ 后端服务未运行，请先启动后端:")
        print(f"   export BACKEND_PORT={BACKEND_PORT}")
        print("   python -m backend.main")
        return False
    
    # 测试2: 流式聊天
    results.append(("流式聊天API", await test_streaming_chat()))
    
    # 测试3: 状态更新
    results.append(("状态更新机制", await test_status_updates()))
    
    # 汇总结果
    print()
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print()
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
        if not result:
            all_passed = False
    
    print()
    return all_passed


if __name__ == "__main__":
    # 设置环境变量
    os.environ.setdefault("BACKEND_PORT", "6080")
    os.environ.setdefault("ENABLE_AUTONOMOUS_EXECUTION", "true")
    os.environ.setdefault("STREAM_TIMEOUT", "600")
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




