#!/usr/bin/env python3
# 时间：2026-04-11；理由：用 .env 中 MediaWiki 配置 + mwclient（经 MediaWikiClientService）验证登录与读接口；方法：load_env 后 connect、verify_read_access、search、get_page
"""
使用仓库 `load_env` 加载的 `.env` / `~/.config/hou-cli/.env`，通过 `MediaWikiClientService`（底层 mwclient）测试：

1. 连接并登录（默认与 MCP 一致：`MEDIAWIKI_LOGIN_ORDER=user_first` 主账号优先；否则受 `MEDIAWIKI_USE_BOT_PASSWORD` 控制）
2. `verify_read_access`（query meta=siteinfo）
3. `search_pages`（默认关键词 `统计学`，可用 argv[1] 覆盖）
4. 若有结果，对第一条 `get_page`

用法（仓库根）：

  python3 scripts/test_mediawiki_mwclient_env.py
  python3 scripts/test_mediawiki_mwclient_env.py hou-cli
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from pathlib import Path

from shared.load_env import load_env, load_env_for_file

load_env(Path(_ROOT))
load_env_for_file(__file__)
# 与 MCP 一致：自检脚本默认主账号优先（可用 MEDIAWIKI_LOGIN_ORDER=bot_first 覆盖）
os.environ.setdefault("MEDIAWIKI_LOGIN_ORDER", "user_first")


def main() -> int:
    from backend.services.mediawiki_client_service import MediaWikiClientService
    from backend.services.mediawiki_client_service.client import MediaWikiClientError

    q = (sys.argv[1] if len(sys.argv) > 1 else "统计学").strip() or "统计学"

    print("MediaWiki（mwclient）登录与读接口自检")
    print("-" * 60)
    url = (os.getenv("MEDIAWIKI_URL") or "").strip()
    print(f"MEDIAWIKI_URL: {url or '(未设置)'}")
    print(
        "USE_BOT_PASSWORD:",
        (os.getenv("MEDIAWIKI_USE_BOT_PASSWORD") or "true").strip(),
        "| USER set:",
        bool((os.getenv("MEDIAWIKI_USERNAME") or "").strip()),
        "| BOT set:",
        bool((os.getenv("MEDIAWIKI_BOT_NAME") or "").strip())
        and bool((os.getenv("MEDIAWIKI_BOT_PASSWORD") or "").strip()),
    )
    print("-" * 60)

    try:
        client = MediaWikiClientService()
        client.connect()
        print("1. connect + login: OK")
    except MediaWikiClientError as e:
        print(f"1. connect + login: FAILED\n   {e}")
        print(
            "   提示: 若 Wiki 提示机器人密码须重置，可仅主账号再测：\n"
            "   MEDIAWIKI_USE_BOT_PASSWORD=false python3 scripts/test_mediawiki_mwclient_env.py"
        )
        return 1

    try:
        ok, msg = client.verify_read_access()
        print(f"2. verify_read_access: {'OK' if ok else 'FAIL'} — {msg}")
        if not ok:
            return 1
    except Exception as e:
        print(f"2. verify_read_access: FAILED — {e}")
        return 1

    try:
        rows = client.search_pages(q, limit=5)
        print(f"3. search_pages({q!r}, limit=5): {len(rows)} 条")
        for i, r in enumerate(rows, 1):
            sn = (r.snippet or "").replace("\n", " ")[:120]
            print(f"   {i}. {r.title}  {sn}")
    except Exception as e:
        print(f"3. search_pages: FAILED — {e}")
        return 1

    if not rows:
        print("4. get_page: 跳过（无搜索结果）")
        return 0

    title = rows[0].title
    try:
        page = client.get_page(title)
        if not page:
            print(f"4. get_page({title!r}): 页面不存在")
            return 1
        body = page.content or ""
        preview = body[:400].replace("\n", " ")
        if len(body) > 400:
            preview += "…"
        print(f"4. get_page({title!r}): OK, len={len(body)}, preview=\n   {preview}")
    except Exception as e:
        print(f"4. get_page: FAILED — {e}")
        return 1

    print("-" * 60)
    print("全部步骤通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
