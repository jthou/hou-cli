#!/usr/bin/env python3
"""
MediaWiki search-read 诊断脚本：验证 .env 加载、连接、登录、搜索。
用法（从项目根执行，必须用 python 不要用 bash）：
  python scripts/test_mediawiki_search_read.py
  python3 scripts/test_mediawiki_search_read.py
"""
import os
import sys
from pathlib import Path

# 项目根
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from shared.load_env import load_env
load_env(ROOT)

# 检查凭据（不输出敏感值）
url = os.getenv("MEDIAWIKI_URL", "")
user = os.getenv("MEDIAWIKI_USERNAME", "")
bot = os.getenv("MEDIAWIKI_BOT_NAME", "")
has_user = bool((user or "").strip())
has_bot = bool((bot or "").strip())
has_pass = bool((os.getenv("MEDIAWIKI_PASSWORD") or "").strip())
has_bot_pass = bool((os.getenv("MEDIAWIKI_BOT_PASSWORD") or "").strip())

print(f"[ENV] MEDIAWIKI_URL: {url or '(空)'}")
print(f"[ENV] MEDIAWIKI_USERNAME: {'已设置' if has_user else '(空)'}")
print(f"[ENV] MEDIAWIKI_BOT_NAME: {'已设置' if has_bot else '(空)'}")
print(f"[ENV] 密码/Bot密码: {'已设置' if (has_pass or has_bot_pass) else '(空)'}")
if not (has_bot or has_user):
    print("[FAIL] 未配置认证，私有 Wiki 会返回 readapidenied")
    sys.exit(1)

# 测试连接与搜索
print("\n[TEST] 连接 MediaWiki...")
try:
    from backend.services.mediawiki_client_service import MediaWikiClientService
    client = MediaWikiClientService()
    client.connect()
    print("[OK] 连接成功")

    print("[TEST] 搜索 'test'...")
    results = client.search_pages("test", limit=3)
    print(f"[OK] 搜索成功，结果数: {len(results)}")
    for r in results[:3]:
        print(f"  - {r.title}")

    print("\n[PASS] 全部通过")
except Exception as e:
    print(f"\n[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
