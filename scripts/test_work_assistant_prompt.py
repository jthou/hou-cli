#!/usr/bin/env python3
"""验证工作助手 API 是否使用正确的系统提示词（WORK_ASSISTANT_SYSTEM_PROMPT）

用法：确保前后端已启动，执行 python scripts/test_work_assistant_prompt.py
"""
import sys
import os
import json
import sqlite3
import time
import urllib.request
import urllib.error
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from shared.load_env import load_env
load_env(project_root)

# 与 Makefile WEB_PORT 一致，兼容 BACKEND_PORT
BACKEND_PORT = os.getenv("WEB_PORT") or os.getenv("BACKEND_PORT") or "8081"
BASE_URL = f"http://127.0.0.1:{BACKEND_PORT}"


def detect_backend_port():
    """尝试检测后端端口（8081 或 6080），使用 urllib 避免 httpx 代理问题"""
    for port in [BACKEND_PORT, "8081", "6080"]:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
            with urllib.request.urlopen(req, timeout=2.0) as r:
                if r.status == 200:
                    return f"http://127.0.0.1:{port}"
        except Exception:
            continue
    return None

WORK_ASSISTANT_PROMPT_PREFIX = "你是软件架构师的工作助手"
OLD_PROMPT = "你是一个智能助手，能够帮助用户解决各种问题。"


def get_latest_audit_request():
    """获取最新的 LLM 审计 request 记录"""
    try:
        from shared.storage_utils import get_storage_manager
        sm = get_storage_manager()
        db_path = sm.get_sqlite_path("llm_audit.db")
    except Exception as e:
        print(f"无法获取审计数据库: {e}")
        return None
    if not db_path or not db_path.exists():
        print(f"审计数据库不存在: {db_path}")
        return None
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT ts, record FROM llm_audit ORDER BY ts DESC LIMIT 50"
        )
        for row in cur.fetchall():
            rec = json.loads(row[1])
            if rec.get("direction") == "request":
                return rec
    finally:
        conn.close()
    return None


def main():
    print("=" * 60)
    print("工作助手系统提示词验证")
    print("=" * 60)
    base = detect_backend_port()
    if not base:
        print(f"❌ 无法连接后端，请确保服务已启动 (尝试端口 8081/6080)")
        return 1
    print(f"API: {base}/api/chat/stream")
    print(f"期望系统提示词以「{WORK_ASSISTANT_PROMPT_PREFIX}」开头")
    print()

    # 1. 调用工作助手 API（使用 urllib 避免 httpx 代理导致 502）
    print("1. 发送工作助手请求 (context_type=work_assistant)...")
    try:
        req = urllib.request.Request(
            f"{base}/api/chat/stream",
            data=json.dumps({
                "message": "请用一句话介绍你自己",
                "context_type": "work_assistant",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            if resp.status != 200:
                print(f"   ❌ 请求失败: {resp.status}")
                return 1
            # 消费流式响应
            for line in resp:
                try:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("status") == "done":
                            break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        print("   ✓ 请求完成")
    except urllib.error.HTTPError as e:
        print(f"   ❌ 请求失败: {e.code}")
        print(f"   {e.read().decode()[:500]}")
        return 1
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return 1

    # 2. 等待审计写入
    time.sleep(1)

    # 3. 查询最新审计记录
    print("\n2. 查询 LLM 审计最新 request 记录...")
    record = get_latest_audit_request()
    if not record:
        print("   ❌ 未找到审计记录")
        return 1

    payload = record.get("payload", {})
    msgs = payload.get("messages", [])
    system_prompt = None
    for m in msgs:
        if m.get("role") == "system":
            system_prompt = m.get("content_preview") or m.get("content", "")
            break

    if not system_prompt:
        print("   ❌ 未找到 system 消息")
        return 1

    print(f"   ts: {record.get('ts')}")
    print(f"   model: {record.get('model')}")
    print(f"   audit_id: {record.get('audit_id')}")
    print()

    # 4. 验证系统提示词
    print("3. 验证系统提示词...")
    print(f"   实际开头: {repr(system_prompt[:80])}...")
    print()

    if system_prompt.startswith(WORK_ASSISTANT_PROMPT_PREFIX):
        print("   ✅ 通过：工作助手使用了正确的系统提示词")
        return 0
    elif system_prompt.strip() == OLD_PROMPT:
        print("   ❌ 失败：仍在使用旧提示词「你是一个智能助手...」")
        return 1
    else:
        print("   ❌ 失败：系统提示词不符合预期")
        print(f"   期望以: 「{WORK_ASSISTANT_PROMPT_PREFIX}」")
        return 1


if __name__ == "__main__":
    sys.exit(main())
