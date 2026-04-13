#!/usr/bin/env python3
# 时间：2026-04-11；理由：写 MediaWiki 长文时需对照维基百科，与 hou-cli WikipediaService 同源；方法：FastMCP stdio + asyncio.to_thread，只读不写
"""
Wikipedia MCP（stdio）：搜索、读摘要/正文、列链接。供 Cursor 与本地 MediaWiki 撰稿对照用。

依赖：`wikipedia` 包（见 requirements.txt）；**无需 API key**。默认语言可由环境变量 `WIKIPEDIA_DEFAULT_LANG` 设置（默认 zh）。

与项目内 `backend/services/wikipedia_service/client.py`、`backend/core/agent/tools/builtin/wikipedia_tool.py` 行为一致。

Cursor `~/.cursor/mcp.json` 示例：

  {
    "mcpServers": {
      "hou-wikipedia": {
        "command": "python3",
        "args": ["/ABS/PATH/TO/hou-cli/scripts/mcp_wikipedia_server.py"],
        "cwd": "/ABS/PATH/TO/hou-cli"
      }
    }
  }

工具一览：
- `hou_wikipedia_ping`：检查能否访问维基 API。
- `hou_wikipedia_search`：按关键词搜索标题（可指定语言）。
- `hou_wikipedia_get_page`：按标题读摘要或全文（可截断）。
- `hou_wikipedia_page_links`：列出条目内链（便于扩展阅读）。
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

load_env(ROOT)
load_env_for_file(__file__)
# 时间：2026-04-11；理由：与后端 Wikipedia 路由一致；方法：可选环境变量，未设时 zh
os.environ.setdefault("WIKIPEDIA_DEFAULT_LANG", "zh")


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _svc(language: str | None) -> Any:
    from backend.services.wikipedia_service import WikipediaService

    lang = (language or os.getenv("WIKIPEDIA_DEFAULT_LANG") or "zh").strip() or "zh"
    return WikipediaService(language=lang)


def _build_mcp():
    from mcp.server.fastmcp import FastMCP
    from backend.services.wikipedia_service import WikipediaServiceError

    mcp = FastMCP(
        "hou_wikipedia",
        instructions=(
            "只读维基百科（Wikipedia.org）。撰写本站 MediaWiki 时请作事实核对与引用来源，"
            "勿整篇复制版权内容；正文以自有表述为主。"
        ),
    )

    @mcp.tool()
    async def hou_wikipedia_ping(language: str = "") -> str:
        """探测当前环境能否调用维基 API（轻量搜索）。"""
        lang_param = (language or "").strip()
        lang = lang_param or (os.getenv("WIKIPEDIA_DEFAULT_LANG") or "zh").strip() or "zh"

        def _run():
            s = _svc(lang)
            q = "数学" if lang.lower().startswith("zh") else "Science"
            r = s.search(q, num_results=1, language=lang_param if lang_param else None)
            return {"ok": True, "language": lang, "sample_hit": r.results[0].title if r.results else None}

        try:
            return _json(await asyncio.to_thread(_run))
        except WikipediaServiceError as e:
            return _json({"ok": False, "error": str(e), "language": lang})
        except Exception as e:
            return _json({"ok": False, "error": str(e), "language": lang})

    @mcp.tool()
    async def hou_wikipedia_search(
        query: str,
        num_results: int = 10,
        language: str = "",
    ) -> str:
        """搜索维基条目标题；num_results 建议 1–20。"""
        q = (query or "").strip()
        if not q:
            return _json({"success": False, "error": "query 为空"})
        lang = (language or os.getenv("WIKIPEDIA_DEFAULT_LANG") or "zh").strip() or "zh"
        n = max(1, min(int(num_results) if num_results else 10, 20))

        def _run():
            s = _svc(lang)
            resp = s.search(q, num_results=n, language=lang if language else None)
            rows = []
            for r in resp.results:
                rows.append(
                    {
                        "title": r.title,
                        "page_id": r.page_id,
                        "url": r.url,
                    }
                )
            return {"query": q, "language": resp.language, "count": len(rows), "results": rows}

        try:
            return _json({"success": True, **(await asyncio.to_thread(_run))})
        except WikipediaServiceError as e:
            return _json({"success": False, "error": str(e)})
        except Exception as e:
            return _json({"success": False, "error": str(e)})

    @mcp.tool()
    async def hou_wikipedia_get_page(
        title: str,
        language: str = "",
        summary_only: bool = True,
        max_content_chars: int = 120_000,
    ) -> str:
        """按标题读取条目：默认仅摘要；summary_only=false 时返回正文（过长截断并注明）。"""
        t = (title or "").strip()
        if not t:
            return _json({"success": False, "error": "title 为空"})
        lang = (language or os.getenv("WIKIPEDIA_DEFAULT_LANG") or "zh").strip() or "zh"
        cap = max(4000, min(int(max_content_chars) if max_content_chars else 120_000, 500_000))

        def _run():
            s = _svc(lang)
            p = s.get_page(t, language=lang if language else None, summary_only=bool(summary_only))
            body = (p.summary or "") if summary_only else ((p.content or "") if p.content else (p.summary or ""))
            truncated = len(body) > cap
            text = body[:cap] if truncated else body
            return {
                "title": p.title,
                "page_id": p.page_id,
                "url": p.url,
                "language": p.language,
                "summary_only": bool(summary_only),
                "text": text,
                "truncated": truncated,
                "text_length": len(body),
            }

        try:
            data = await asyncio.to_thread(_run)
            return _json({"success": True, "page": data})
        except WikipediaServiceError as e:
            return _json({"success": False, "error": str(e)})
        except Exception as e:
            return _json({"success": False, "error": str(e)})

    @mcp.tool()
    async def hou_wikipedia_page_links(
        title: str,
        limit: int = 80,
        language: str = "",
    ) -> str:
        """列出条目正文中的内部链接标题（便于扩展阅读）；limit 默认 80，最大 500。"""
        t = (title or "").strip()
        if not t:
            return _json({"success": False, "error": "title 为空"})
        lang = (language or os.getenv("WIKIPEDIA_DEFAULT_LANG") or "zh").strip() or "zh"
        lim = max(1, min(int(limit) if limit else 80, 500))

        def _run():
            s = _svc(lang)
            r = s.get_page_links(t, language=lang if language else None, limit=lim)
            return {
                "title": r.title,
                "url": r.url,
                "language": r.language,
                "links": r.links,
                "links_count": r.links_count,
            }

        try:
            data = await asyncio.to_thread(_run)
            return _json({"success": True, **data})
        except WikipediaServiceError as e:
            return _json({"success": False, "error": str(e)})
        except Exception as e:
            return _json({"success": False, "error": str(e)})

    return mcp


def main() -> None:
    os.environ.setdefault("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", "true")
    try:
        lang = (os.getenv("WIKIPEDIA_DEFAULT_LANG") or "zh").strip()
        print("[hou-wikipedia MCP] python=", sys.executable, "cwd=", os.getcwd(), "default_lang=", lang, file=sys.stderr, flush=True)
    except Exception:
        pass
    mcp = _build_mcp()
    mcp.run()


if __name__ == "__main__":
    main()
