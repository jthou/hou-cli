#!/usr/bin/env python3
"""测试 /context clear 和 /context show 命令"""
import sys
import os
import requests
import time
sys.path.insert(0, os.getcwd())

# 读取端口
try:
    with open('port.txt', 'r') as f:
        port = int(f.read().strip())
except:
    port = 8000

base_url = f"http://127.0.0.1:{port}"

print(f"测试后端API: {base_url}\n")

# 等待后端启动
print("1. 等待后端启动...")
for i in range(10):
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        if response.status_code == 200:
            print(f"   ✅ 健康检查通过: {response.status_code}")
            break
    except:
        if i < 9:
            time.sleep(1)
            continue
        print(f"   ❌ 健康检查失败: 后端未启动")
        sys.exit(1)

# 获取或创建测试会话
print("\n2. 获取测试会话...")
try:
    response = requests.get(f"{base_url}/api/sessions/list?limit=1", timeout=5)
    if response.status_code == 200:
        data = response.json()
        sessions = data.get('sessions', [])
        if sessions:
            test_session_id = sessions[0].get('session_id')
            print(f"   ✅ 使用现有会话: {test_session_id[:8]}...")
        else:
            # 创建新会话
            response = requests.post(f"{base_url}/api/sessions", timeout=5)
            if response.status_code == 200:
                data = response.json()
                test_session_id = data.get('session_id')
                print(f"   ✅ 创建新会话: {test_session_id[:8]}...")
            else:
                print(f"   ❌ 创建会话失败: {response.status_code}")
                sys.exit(1)
    else:
        print(f"   ❌ 获取会话列表失败: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ 错误: {e}")
    sys.exit(1)

# 测试 GET /api/sessions/{session_id}
print(f"\n3. 测试 GET /api/sessions/{test_session_id[:8]}...")
try:
    response = requests.get(f"{base_url}/api/sessions/{test_session_id}", timeout=5)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"   ✅ 成功获取会话详情")
            print(f"      消息数量: {len(data.get('messages', []))}")
        else:
            print(f"   ⚠️  返回失败: {data.get('error', 'N/A')}")
    else:
        print(f"   ❌ HTTP错误: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 测试 POST /api/sessions/{session_id}/clear
print(f"\n4. 测试 POST /api/sessions/{test_session_id[:8]}/clear...")
try:
    response = requests.post(f"{base_url}/api/sessions/{test_session_id}/clear", timeout=5)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"   ✅ 成功清除会话消息")
            print(f"      消息: {data.get('message', 'N/A')}")
        else:
            print(f"   ⚠️  返回失败: {data.get('error', 'N/A')}")
    else:
        print(f"   ❌ HTTP错误: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 测试前端命令处理
print("\n5. 测试前端命令处理...")
try:
    from frontend.client.ipc_client import IPCClient
    from frontend.ui.command_handler import CommandHandler
    
    client = IPCClient()
    handler = CommandHandler(client=client, current_session_id=test_session_id)
    
    # 测试 /context clear
    print("   测试 /context clear...")
    result, _ = handler.handle_command("/context clear")
    if result and "错误" not in result and "HTTP 错误" not in result:
        print(f"   ✅ /context clear 成功")
        print(f"      结果: {result[:80]}...")
    else:
        print(f"   ❌ /context clear 失败: {result[:100] if result else 'None'}")
    
    # 测试 /context show
    print("   测试 /context show...")
    result, _ = handler.handle_command("/context show")
    if result and "错误" not in result and "HTTP 错误" not in result:
        print(f"   ✅ /context show 成功")
        print(f"      结果: {result[:80]}...")
    else:
        print(f"   ❌ /context show 失败: {result[:100] if result else 'None'}")
        
except Exception as e:
    print(f"   ❌ 前端命令处理测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ 测试完成")
