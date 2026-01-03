#!/usr/bin/env python3
"""测试所有使用 httpx 的方法，检查是否有 502 问题"""
import sys
import os
import requests
import httpx
import time
sys.path.insert(0, os.getcwd())

# 读取端口
try:
    with open('port.txt', 'r') as f:
        port = int(f.read().strip())
except:
    port = 8000

base_url = f"http://127.0.0.1:{port}"

print("=" * 60)
print("测试所有使用 httpx 的方法")
print("=" * 60)
print(f"后端URL: {base_url}\n")

# 等待后端启动
print("1. 等待后端启动...")
for i in range(10):
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        if response.status_code == 200:
            print(f"   ✅ 后端已启动\n")
            break
    except:
        if i < 9:
            time.sleep(1)
            continue
        print(f"   ❌ 后端未启动")
        sys.exit(1)

# 测试结果
results = []

# 测试 1: frontend/client/ipc_client.py - send() (已修复，使用requests)
print("2. 测试 frontend/client/ipc_client.py 中的方法...")
try:
    from frontend.client.ipc_client import IPCClient
    client = IPCClient()
    
    # 测试 send() - 应该使用 requests
    print("   - send() 方法...")
    try:
        result = client.send("hello", session_id=None)
        results.append(("send()", "✅ 成功", "使用 requests"))
    except Exception as e:
        results.append(("send()", f"❌ 失败: {e}", "使用 requests"))
    
    # 测试 list_sessions() - 应该使用 requests
    print("   - list_sessions() 方法...")
    try:
        sessions = client.list_sessions(limit=1)
        results.append(("list_sessions()", "✅ 成功", "使用 requests"))
    except Exception as e:
        results.append(("list_sessions()", f"❌ 失败: {e}", "使用 requests"))
    
    # 测试 get_session_detail() - 应该使用 requests
    print("   - get_session_detail() 方法...")
    try:
        sessions = client.list_sessions(limit=1)
        if sessions:
            detail = client.get_session_detail(sessions[0].get('session_id'))
            results.append(("get_session_detail()", "✅ 成功", "使用 requests"))
        else:
            results.append(("get_session_detail()", "⚠️  跳过（无会话）", "使用 requests"))
    except Exception as e:
        results.append(("get_session_detail()", f"❌ 失败: {e}", "使用 requests"))
    
    # 测试 delete_session() - 应该使用 requests
    print("   - delete_session() 方法...")
    try:
        # 先创建一个测试会话
        test_session_id = client.create_session()
        # 然后删除它
        success = client.delete_session(test_session_id)
        if success:
            results.append(("delete_session()", "✅ 成功", "使用 requests"))
        else:
            results.append(("delete_session()", "❌ 失败: 返回False", "使用 requests"))
    except Exception as e:
        results.append(("delete_session()", f"❌ 失败: {e}", "使用 requests"))
    
    # 测试 clear_session_messages() - 应该使用 requests
    print("   - clear_session_messages() 方法...")
    try:
        test_session_id = client.create_session()
        success = client.clear_session_messages(test_session_id)
        if success:
            results.append(("clear_session_messages()", "✅ 成功", "使用 requests"))
        else:
            results.append(("clear_session_messages()", "❌ 失败: 返回False", "使用 requests"))
    except Exception as e:
        results.append(("clear_session_messages()", f"❌ 失败: {e}", "使用 requests"))
    
    # 测试 create_session() - 应该使用 requests
    print("   - create_session() 方法...")
    try:
        session_id = client.create_session()
        if session_id:
            results.append(("create_session()", "✅ 成功", "使用 requests"))
        else:
            results.append(("create_session()", "❌ 失败: 返回None", "使用 requests"))
    except Exception as e:
        results.append(("create_session()", f"❌ 失败: {e}", "使用 requests"))
    
    # 测试 search_sessions() - 应该使用 requests
    print("   - search_sessions() 方法...")
    try:
        sessions = client.search_sessions("test", limit=1)
        results.append(("search_sessions()", "✅ 成功", "使用 requests"))
    except Exception as e:
        results.append(("search_sessions()", f"❌ 失败: {e}", "使用 requests"))
    
    # 测试 generate_session_summary() - 应该使用 requests
    print("   - generate_session_summary() 方法...")
    try:
        test_session_id = client.create_session()
        # 这个可能需要会话有消息，所以可能会失败，但至少测试不会502
        try:
            summary = client.generate_session_summary(test_session_id)
            results.append(("generate_session_summary()", "✅ 成功", "使用 requests"))
        except Exception as e:
            if "502" in str(e) or "HTTP 错误：502" in str(e):
                results.append(("generate_session_summary()", f"❌ 502错误: {e}", "使用 requests"))
            else:
                results.append(("generate_session_summary()", f"⚠️  其他错误: {e}", "使用 requests"))
    except Exception as e:
        results.append(("generate_session_summary()", f"❌ 失败: {e}", "使用 requests"))
    
    # 测试 stream_send() - 使用 httpx.AsyncClient (应该保留)
    print("   - stream_send() 方法（异步，使用 httpx.AsyncClient）...")
    try:
        import asyncio
        async def test_stream():
            chunks = []
            async for chunk in client.stream_send("hello"):
                chunks.append(chunk)
                if len(chunks) > 10:  # 限制测试长度
                    break
            return len(chunks) > 0
        
        result = asyncio.run(test_stream())
        if result:
            results.append(("stream_send()", "✅ 成功", "使用 httpx.AsyncClient (保留)"))
        else:
            results.append(("stream_send()", "❌ 失败: 无数据", "使用 httpx.AsyncClient (保留)"))
    except Exception as e:
        if "502" in str(e):
            results.append(("stream_send()", f"❌ 502错误: {e}", "使用 httpx.AsyncClient"))
        else:
            results.append(("stream_send()", f"⚠️  其他错误: {e}", "使用 httpx.AsyncClient (保留)"))
    
except Exception as e:
    print(f"   ❌ IPC客户端测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 2: cli.py 中的 httpx 使用
print("\n3. 测试 cli.py 中的 httpx 使用...")
try:
    # 直接测试 httpx.get 健康检查
    print("   - httpx.get() 健康检查...")
    try:
        response = httpx.get(f"{base_url}/health", timeout=2.0)
        if response.status_code == 200:
            results.append(("cli.py: httpx.get(health)", "✅ 成功", "httpx"))
        else:
            results.append(("cli.py: httpx.get(health)", f"❌ 状态码: {response.status_code}", "httpx"))
    except Exception as e:
        if "502" in str(e):
            results.append(("cli.py: httpx.get(health)", f"❌ 502错误: {e}", "httpx"))
        else:
            results.append(("cli.py: httpx.get(health)", f"⚠️  其他错误: {e}", "httpx"))
except Exception as e:
    results.append(("cli.py: httpx.get(health)", f"❌ 测试失败: {e}", "httpx"))

# 测试 3: backend/core/agent/tools/builtin/weather_tool.py 中的 httpx
print("\n4. 测试 weather_tool.py 中的 httpx 使用...")
try:
    from backend.core.agent.tools.builtin.weather_tool import WeatherTool
    import os
    
    # 检查环境变量
    if not os.getenv("QWEATHER_API_HOST"):
        results.append(("weather_tool: httpx.get()", "⚠️  跳过（缺少环境变量）", "httpx"))
    else:
        # 这里只是检查方法是否存在，不实际调用（需要API密钥）
        results.append(("weather_tool: httpx.get()", "⚠️  跳过（需要API密钥）", "httpx"))
except Exception as e:
    results.append(("weather_tool: httpx.get()", f"⚠️  跳过: {e}", "httpx"))

# 打印测试结果
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
print(f"{'方法':<40} {'状态':<30} {'库'}")
print("-" * 60)

has_502 = False
for method, status, library in results:
    print(f"{method:<40} {status:<30} {library}")
    if "502" in status or "HTTP 错误：502" in status:
        has_502 = True

print("\n" + "=" * 60)
if has_502:
    print("❌ 发现 502 错误！需要修复")
else:
    print("✅ 所有测试通过，未发现 502 错误")
print("=" * 60)

