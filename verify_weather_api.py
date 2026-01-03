#!/usr/bin/env python3
"""验证和风天气 API 配置"""
import httpx
import os
import jwt
import time
from dotenv import load_dotenv
from backend.core.agent.tools.auth.jwt_auth import JWTAuth

load_dotenv()

print("=" * 60)
print("JWT 和 API 配置验证")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 环境变量检查:")
print(f"   QWEATHER_CREDENTIAL_ID: {os.getenv('QWEATHER_CREDENTIAL_ID', 'NOT SET')}")
print(f"   QWEATHER_PROJECT_ID: {os.getenv('QWEATHER_PROJECT_ID', 'NOT SET')}")
print(f"   WEATHER_JWT_PRIVATE_KEY: {'SET' if os.getenv('WEATHER_JWT_PRIVATE_KEY') else 'NOT SET'}")

# 2. 创建 JWT Auth
print("\n2. JWT Auth 创建:")
try:
    jwt_auth = JWTAuth.from_env()
    print(f"   ✓ JWT Auth 创建成功")
    print(f"   kid: {jwt_auth.kid}")
    print(f"   sub: {jwt_auth.sub}")
except Exception as e:
    print(f"   ✗ JWT Auth 创建失败: {e}")
    exit(1)

# 3. 生成 JWT Token
print("\n3. JWT Token 生成:")
try:
    token = jwt_auth.generate_token()
    print(f"   ✓ Token 生成成功")
    print(f"   Token 长度: {len(token)}")
    print(f"   Token 预览: {token[:80]}...")
    
    # 解码 token（不验证签名）
    decoded_header = jwt.get_unverified_header(token)
    decoded_payload = jwt.decode(token, options={"verify_signature": False})
    
    print(f"\n   Token Header:")
    print(f"     alg: {decoded_header.get('alg')}")
    print(f"     kid: {decoded_header.get('kid')}")
    
    print(f"\n   Token Payload:")
    print(f"     sub: {decoded_payload.get('sub')}")
    print(f"     iat: {decoded_payload.get('iat')} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(decoded_payload.get('iat')))})")
    print(f"     exp: {decoded_payload.get('exp')} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(decoded_payload.get('exp')))})")
    
except Exception as e:
    print(f"   ✗ Token 生成失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 4. 测试 API 调用
print("\n4. API 调用测试:")
params = {'location': '北京'}
headers = jwt_auth.get_authorization_header()

print(f"   Endpoint: {endpoint}")
print(f"   Params: {params}")
print(f"   Authorization: {headers['Authorization'][:60]}...")

try:
    response = httpx.get(endpoint, params=params, headers=headers, timeout=10.0)
    print(f"\n   Response Status: {response.status_code}")
    print(f"   Response Headers:")
    for key, value in response.headers.items():
        if key.lower() in ['content-type', 'content-length', 'x-ratelimit']:
            print(f"     {key}: {value}")
    
    print(f"\n   Response Body:")
    if response.text:
        print(f"     {response.text[:500]}")
    else:
        print(f"     (empty)")
    
    if response.status_code == 200:
        print(f"\n   ✓ API 调用成功!")
        data = response.json()
        if data.get('code') == '200':
            print(f"   ✓ 城市搜索成功")
            locations = data.get('location', [])
            if locations:
                print(f"   找到 {len(locations)} 个城市:")
                for loc in locations[:3]:
                    print(f"     - {loc.get('name')} (ID: {loc.get('id')})")
        else:
            print(f"   ✗ API 返回错误: {data.get('code')} - {data.get('refer')}")
    elif response.status_code == 401:
        print(f"\n   ✗ 认证失败 (401) - 请检查 JWT token 是否正确")
    elif response.status_code == 404:
        print(f"\n   ✗ 端点不存在 (404) - 请检查 API URL 是否正确")
    else:
        print(f"\n   ✗ API 调用失败: {response.status_code}")
        
except Exception as e:
    print(f"   ✗ API 调用异常: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

