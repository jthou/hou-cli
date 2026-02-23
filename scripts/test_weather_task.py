#!/usr/bin/env python3
"""
开发环境：创建天气预报任务并轮询结果。
用法（项目根目录）：
  python scripts/test_weather_task.py [城市] [current|forecast]
  例如：python scripts/test_weather_task.py 北京 current
        python scripts/test_weather_task.py 上海 forecast
若未传参，默认：北京、current。
需先启动后端（make run-backend 或 make start）。
"""
import os
import sys
import time

# 保证项目根在 path 中
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

def get_base_url():
    port = os.getenv("WEB_PORT") or os.getenv("BACKEND_PORT")
    if port:
        return f"http://127.0.0.1:{int(port)}"
    try:
        from shared.platform_utils import load_port
        return f"http://127.0.0.1:{load_port()}"
    except Exception:
        return "http://127.0.0.1:8081"

def main():
    location = (sys.argv[1] if len(sys.argv) > 1 else "北京").strip()
    query_type = (sys.argv[2] if len(sys.argv) > 2 else "current").strip()
    if query_type not in ("current", "forecast"):
        query_type = "current"

    base = get_base_url()
    api = f"{base}/api/task-queue"

    try:
        import httpx
    except ImportError:
        print("请安装 httpx: pip install httpx")
        sys.exit(1)

    # 健康检查（可选：先试一次，失败也继续尝试创建任务）
    try:
        r = httpx.get(f"{base}/health", timeout=3.0)
        if r.status_code == 200:
            print(f"后端: {base}")
    except Exception:
        print(f"提示: 若创建失败请先启动后端 make run-backend，并确认端口 {base}")

    # 创建任务
    payload = {
        "task_type": "weather_query",
        "metadata": {"location": location, "query_type": query_type},
    }
    print(f"创建任务: {location} {'天气预报' if query_type == 'forecast' else '实时天气'} ...")
    try:
        r = httpx.post(f"{api}/tasks", json=payload, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            print("创建失败:", data)
            sys.exit(3)
        task_id = data["task_id"]
        print(f"任务已创建: task_id={task_id}")
    except httpx.HTTPStatusError as e:
        print(f"创建任务失败 HTTP {e.response.status_code}: {e.response.text}")
        sys.exit(3)
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        print(f"无法连接后端 {base}，请先启动: make run-backend\n错误: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"创建任务失败: {e}")
        sys.exit(3)

    # 轮询结果
    print("轮询结果（每 2 秒）...")
    while True:
        try:
            r = httpx.get(f"{api}/tasks/{task_id}", timeout=5.0)
            r.raise_for_status()
            body = r.json()
            if not body.get("success"):
                print("获取任务失败:", body)
                sys.exit(4)
            task = body["task"]
            status = task.get("status")
            progress = task.get("progress", 0)
            message = task.get("message") or ""

            if status == "running":
                print(f"  状态: {status}  进度: {progress}%  {message}")
            elif status == "completed":
                result = task.get("result") or {}
                print("\n✅ 任务完成")
                print(f"   摘要: {result.get('summary', '')}")
                res = result.get("result", {})
                if res.get("current_weather"):
                    c = res["current_weather"]
                    if isinstance(c, dict):
                        print(f"   当前: {c.get('text', '')} {c.get('temp', '')}°C")
                if res.get("forecast"):
                    print("   预报数据已返回（见 result.forecast）")
                break
            elif status == "failed":
                print("\n❌ 任务失败")
                print(f"   错误: {task.get('error', '')}")
                sys.exit(5)
            elif status == "cancelled":
                print("\n⏹ 任务已取消")
                sys.exit(6)
            else:
                print(f"  状态: {status}  {message}")
        except Exception as e:
            print(f"轮询异常: {e}")
        time.sleep(2)

if __name__ == "__main__":
    main()
