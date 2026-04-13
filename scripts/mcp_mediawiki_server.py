#!/usr/bin/env python3
# 时间：2026-04-11；理由：在 Cursor 内通过 MCP 读写本仓库配置的 MediaWiki（与 hou-cli API 同源 mwclient）；方法：FastMCP stdio + MediaWikiClientService + asyncio.to_thread
"""
MediaWiki MCP（stdio）：搜索、读取页面 wikitext、保存页面。

依赖：仓库根 `cwd`、`.env` 中至少 `MEDIAWIKI_URL`；私有 Wiki 需 `MEDIAWIKI_BOT_NAME`/`MEDIAWIKI_BOT_PASSWORD`
或 `MEDIAWIKI_USERNAME`/`MEDIAWIKI_PASSWORD`（与 `backend/services/mediawiki_client_service/client.py` 一致）。

Cursor 配置示例（`~/.cursor/mcp.json`）：

  {
    "mcpServers": {
      "hou-mediawiki": {
        "command": "python3",
        "args": ["/ABS/PATH/TO/hou-cli/scripts/mcp_mediawiki_server.py"],
        "cwd": "/ABS/PATH/TO/hou-cli"
      }
    }
  }

工具一览：
- `hou_mediawiki_search`：关键词搜索。
- `hou_mediawiki_get_page`：按标题读取完整 wikitext（过长时截断并注明）。
- `hou_mediawiki_save_page`：写入 wikitext（页面不存在则创建）。
- `hou_mediawiki_parse_preview`：wikitext → HTML 片段（预览用）。
- `hou_mediawiki_ping`：连通性与读权限探测。
- `hou_mediawiki_env_diagnostic`：排查用，返回当前进程是否看到 URL/账号等（**不含密码明文**）。hou-cli 能连而 MCP 不能时先调这个。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.load_env import load_env, load_env_for_file

# 与 main.py 一致：先按仓库根加载；再按本文件推断根（双保险）。不继承「终端里 export」的变量，凭据须在 .env 文件中。
load_env(ROOT)
load_env_for_file(__file__)
# MCP 默认主账号优先：避免 Wiki 侧「机器人密码须重置」挡掉整条连接（hou-cli 后端未设该变量时仍为 bot_first）
os.environ.setdefault("MEDIAWIKI_LOGIN_ORDER", "user_first")

_DEFAULT_MAX_GET = 800_000


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _env_diagnostic_payload() -> dict[str, Any]:
    """时间：2026-04-11；理由：hou-cli 后端与 Cursor MCP 进程环境常不一致；方法：只返回是否「有配置」与路径，不泄露密钥。"""
    cfg = Path.home() / ".config" / "hou-cli" / ".env"
    root_env = ROOT / ".env"
    cwd_env = Path.cwd() / ".env"
    use_bot = (os.getenv("MEDIAWIKI_USE_BOT_PASSWORD") or "true").strip().lower() not in (
        "0", "false", "no", "off",
    )
    url = (os.getenv("MEDIAWIKI_URL") or "").strip()
    user = (os.getenv("MEDIAWIKI_USERNAME") or "").strip()
    pw = (os.getenv("MEDIAWIKI_PASSWORD") or "").strip()
    bn = (os.getenv("MEDIAWIKI_BOT_NAME") or "").strip()
    bp = (os.getenv("MEDIAWIKI_BOT_PASSWORD") or "").strip()
    login_order = (os.getenv("MEDIAWIKI_LOGIN_ORDER") or "bot_first").strip().lower()
    return {
        "python": sys.executable,
        "cwd": os.getcwd(),
        "repo_root_guess": str(ROOT),
        "env_files": {
            "hou_cli_dotenv_exists": root_env.is_file(),
            "hou_cli_dotenv_path": str(root_env),
            "config_hou_cli_dotenv_exists": cfg.is_file(),
            "config_hou_cli_dotenv_path": str(cfg),
            "cwd_dotenv_exists": cwd_env.is_file(),
            "cwd_dotenv_path": str(cwd_env.resolve()),
        },
        "mediawiki": {
            "MEDIAWIKI_URL_configured": bool(url),
            "MEDIAWIKI_URL_host_hint": (url.split("//")[-1].split("/")[0][:80] if url else ""),
            "MEDIAWIKI_USERNAME_set": bool(user),
            "MEDIAWIKI_PASSWORD_set": bool(pw),
            "MEDIAWIKI_BOT_NAME_set": bool(bn),
            "MEDIAWIKI_BOT_PASSWORD_set": bool(bp),
            "MEDIAWIKI_USE_BOT_PASSWORD": use_bot,
            "MEDIAWIKI_LOGIN_ORDER": login_order,
        },
        "hint": "若此处 USER/PASS 为 false 而后端能连：凭据可能只在 shell export 里；请写入 hou-cli/.env 或 ~/.config/hou-cli/.env。若 python 与启动 hou-cli 的解释器不同，请在 mcp.json 里把 command 改为同一 venv 的 python。",
    }


def _build_mcp():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "hou_mediawiki",
        instructions=(
            "读写由 hou-cli 环境变量 MEDIAWIKI_URL 等配置的 MediaWiki。"
            "正文为 wikitext；保存前请 hou_mediawiki_get_page 取当前版本以免覆盖他人编辑。"
        ),
    )

    def _mw_cls():
        from backend.services.mediawiki_client_service import MediaWikiClientService

        return MediaWikiClientService

    @mcp.tool()
    async def hou_mediawiki_env_diagnostic() -> str:
        """排查 MCP 进程是否加载到 Wiki 相关环境变量（布尔与路径，无密码明文）。hou-cli 能连而 MCP 不能时先执行。"""
        return _json(_env_diagnostic_payload())

    @mcp.tool()
    async def hou_mediawiki_ping() -> str:
        """检测 MEDIAWIKI_URL 与登录（若有）是否可读。"""
        MW = _mw_cls()

        def _run():
            c = MW()
            c.connect()
            ok, msg = c.verify_read_access()
            return {"connected": True, "read_ok": ok, "message": msg, "base_url": (c.url or "").rstrip("/")}

        try:
            return _json(await asyncio.to_thread(_run))
        except Exception as e:
            return _json({"connected": False, "error": str(e)})

    @mcp.tool()
    async def hou_mediawiki_search(query: str, limit: int = 15) -> str:
        """搜索页面标题与摘要。limit 1–50。"""
        MW = _mw_cls()
        q = (query or "").strip()
        if not q:
            return _json({"success": False, "error": "query 为空"})

        def _run():
            c = MW()
            c.connect()
            lim = max(1, min(int(limit) if limit else 15, 50))
            rows = c.search_pages(q, limit=lim)
            return [
                {
                    "title": r.title,
                    "snippet": r.snippet,
                    "url": r.url,
                    "score": r.score,
                }
                for r in rows
            ]

        try:
            out = await asyncio.to_thread(_run)
            return _json({"success": True, "count": len(out), "results": out})
        except Exception as e:
            return _json({"success": False, "error": str(e)})

    @mcp.tool()
    async def hou_mediawiki_get_page(page_title: str, max_content_chars: int = _DEFAULT_MAX_GET) -> str:
        """读取页面 wikitext。page_title 为完整标题（可含子页面斜杠）。"""
        MW = _mw_cls()
        t = (page_title or "").strip()
        if not t:
            return _json({"success": False, "error": "page_title 为空"})

        def _run():
            c = MW()
            c.connect()
            p = c.get_page(t)
            if not p:
                return None
            cap = max(4000, min(int(max_content_chars) if max_content_chars else _DEFAULT_MAX_GET, 2_000_000))
            body = p.content or ""
            truncated = len(body) > cap
            text = body[:cap] if truncated else body
            return {
                "title": p.title,
                "url": p.url,
                "categories": p.categories,
                "revision_id": p.revision_id,
                "last_modified": p.last_modified.isoformat() if p.last_modified else "",
                "content": text,
                "truncated": truncated,
                "content_length": len(body),
            }

        try:
            data = await asyncio.to_thread(_run)
            if data is None:
                return _json({"success": False, "error": f"页面不存在: {t}"})
            return _json({"success": True, "page": data})
        except Exception as e:
            return _json({"success": False, "error": str(e)})

    @mcp.tool()
    async def hou_mediawiki_save_page(
        page_title: str,
        wikitext: str,
        summary: str = "MCP: hou_mediawiki_save_page",
        minor: bool = False,
    ) -> str:
        """保存页面（wikitext）。不存在则创建；存在则覆盖，请先 get_page 合并。"""
        MW = _mw_cls()
        t = (page_title or "").strip()
        body = wikitext if isinstance(wikitext, str) else str(wikitext or "")
        if not t:
            return _json({"success": False, "error": "page_title 为空"})

        def _run():
            c = MW()
            c.connect()
            ok = c.edit_page(t, body, summary=(summary or "MCP edit").strip()[:500], minor=bool(minor))
            return bool(ok)

        try:
            ok = await asyncio.to_thread(_run)
            return _json({"success": ok, "page_title": t, "message": "已保存" if ok else "保存失败"})
        except Exception as e:
            return _json({"success": False, "error": str(e), "page_title": t})

    @mcp.tool()
    async def hou_mediawiki_parse_preview(wikitext: str, page_title: str = "") -> str:
        """将 wikitext 解析为 HTML 片段（仅预览，不写站）。"""
        MW = _mw_cls()
        wt = wikitext if isinstance(wikitext, str) else str(wikitext or "")
        if not wt.strip():
            return _json({"success": False, "error": "wikitext 为空"})
        tit = (page_title or "").strip() or None

        def _run():
            c = MW()
            c.connect()
            html = c.parse_wikitext(wt, title=tit)
            cap = 400_000
            truncated = len(html) > cap
            return {"html": html[:cap] if truncated else html, "truncated": truncated, "length": len(html)}

        try:
            data = await asyncio.to_thread(_run)
            return _json({"success": True, **data})
        except Exception as e:
            return _json({"success": False, "error": str(e)})

    return mcp


def main() -> None:
    os.environ.setdefault("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", "true")
    # 启动时一行诊断到 stderr，便于在 Cursor「MCP 日志」里对照 hou-cli 后端进程
    try:
        d = _env_diagnostic_payload()
        print(
            "[hou-mediawiki MCP]",
            "python=", d["python"],
            "cwd=", d["cwd"],
            "URL_set=", d["mediawiki"]["MEDIAWIKI_URL_configured"],
            "USER_PASS_set=", d["mediawiki"]["MEDIAWIKI_USERNAME_set"] and d["mediawiki"]["MEDIAWIKI_PASSWORD_set"],
            "BOT_set=", d["mediawiki"]["MEDIAWIKI_BOT_NAME_set"] and d["mediawiki"]["MEDIAWIKI_BOT_PASSWORD_set"],
            "USE_BOT=", d["mediawiki"]["MEDIAWIKI_USE_BOT_PASSWORD"],
            "root_.env=", d["env_files"]["hou_cli_dotenv_exists"],
            file=sys.stderr,
            flush=True,
        )
    except Exception:
        pass
    mcp = _build_mcp()
    mcp.run()


if __name__ == "__main__":
    main()
