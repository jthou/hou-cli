#!/usr/bin/env python3
"""
诊断天气 API 超时：用与后端相同的 env 和请求路径实测连接/读取耗时，并可复现 read/connect 超时。
用法（项目根目录）：
  python scripts/diagnose_weather_timeout.py              # 正常请求，打印总耗时
  python scripts/diagnose_weather_timeout.py --read 5    # 将 read 超时设为 5s，复现 read timeout
  python scripts/diagnose_weather_timeout.py --connect 3  # 将 connect 超时设为 3s，复现 connect timeout
"""
import os
import sys
import time
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from shared.load_env import load_env
load_env(_root)


def main():
    import argparse
    p = argparse.ArgumentParser(description="诊断和风天气 API 超时")
    p.add_argument("--read", type=float, default=None, help="读取超时(秒)，用于复现 read timeout")
    p.add_argument("--connect", type=float, default=None, help="连接超时(秒)，用于复现 connect timeout")
    p.add_argument("--location", default="北京", help="城市名，默认北京")
    args = p.parse_args()

    try:
        from backend.core.agent.tools.auth.jwt_auth import JWTAuth
        from backend.core.agent.tools.builtin.weather_tool import WeatherTool, WeatherToolError
        import httpx
    except ImportError as e:
        print(f"依赖缺失: {e}")
        sys.exit(1)

    if not os.getenv("QWEATHER_API_HOST") or not os.getenv("WEATHER_JWT_PRIVATE_KEY"):
        print("请配置 .env: QWEATHER_API_HOST, WEATHER_JWT_PRIVATE_KEY 等")
        sys.exit(2)

    jwt_auth = JWTAuth.from_env()
    tool = WeatherTool(jwt_auth=jwt_auth)

    # 用一次 search_city 拿到 location id，再请求预报（与任务路径一致）
    print(f"城市: {args.location}")
    try:
        city_id = tool._resolve_location(args.location)
    except WeatherToolError as e:
        print(f"解析城市失败: {e}")
        sys.exit(3)
    print(f"城市ID: {city_id}")

    # 若指定了超时，直接调 httpx 用相同 URL/header 复现超时类型
    base_url = tool._get_api_base_url()
    endpoint = f"{base_url}/v7/weather/7d"
    params = {"location": city_id}
    headers = jwt_auth.get_authorization_header()

    connect = args.connect if args.connect is not None else 25.0
    read = args.read if args.read is not None else 35.0
    # 当前 httpx 要求提供 default 或全部四参数
    timeout = httpx.Timeout(read, connect=connect, read=read)
    print(f"超时设置: connect={connect}s, read={read}s")

    print("请求预报 API (GET /v7/weather/7d)...")
    t0 = time.perf_counter()
    try:
        resp = httpx.get(endpoint, params=params, headers=headers, timeout=timeout)
        elapsed = time.perf_counter() - t0
        resp.raise_for_status()
        data = resp.json()
        daily = (data.get("daily") or []) if isinstance(data, dict) else []
        print(f"成功  耗时: {elapsed:.2f}s  预报天数: {len(daily)}")
        if daily:
            d = daily[0]
            print(f"首日: {d.get('fxDate')} {d.get('textDay')} {d.get('tempMin')}~{d.get('tempMax')}°C")
    except httpx.ReadTimeout as e:
        elapsed = time.perf_counter() - t0
        print(f"复现: Read timeout  耗时: {elapsed:.2f}s  -> {e}")
        sys.exit(10)
    except httpx.ConnectTimeout as e:
        elapsed = time.perf_counter() - t0
        print(f"复现: Connect timeout  耗时: {elapsed:.2f}s  -> {e}")
        sys.exit(11)
    except httpx.RequestError as e:
        elapsed = time.perf_counter() - t0
        print(f"请求错误  耗时: {elapsed:.2f}s  -> {type(e).__name__}: {e}")
        sys.exit(12)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"异常  耗时: {elapsed:.2f}s  -> {type(e).__name__}: {e}")
        sys.exit(13)


if __name__ == "__main__":
    main()
