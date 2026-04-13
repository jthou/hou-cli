#!/usr/bin/env python3
# 时间：2026-04-11；理由：Cursor 内通过 MCP 直接写入微信公众号草稿箱（与任务 wechat_mp_draft 同源逻辑）；方法：FastMCP stdio + process_wechat_mp_draft_task + article_markdown_to_wechat_html
"""
微信公众号草稿 MCP（stdio）。

依赖：`.env` 中 `WECHAT_MP_APP_ID`、`WECHAT_MP_APP_SECRET`；仓库根在 `cwd` 下执行以便 `load_env` 与 `backend` 包可用。

Cursor 配置示例（`~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`）：

  {
    "mcpServers": {
      "hou-wechat-mp-draft": {
        "command": "python3",
        "args": ["/ABS/PATH/TO/hou-cli/scripts/mcp_wechat_mp_draft_server.py"],
        "cwd": "/ABS/PATH/TO/hou-cli"
      }
    }
  }

工具：`hou_wechat_mp_draft_publish`
- `operation`: `add`（新建草稿）或 `update`（更新已有草稿，`media_id` 必填）。
- 正文：`article_markdown` 与 `article_html` 二选一（优先使用非空的 `article_html`）。
- `title` 可空；仅 Markdown 且标题空时，会尝试用首行 `# 标题` 填标题。
- `digest` 超过 120 字自动截断；`thumb_media_id` 选填（无效时任务内会省略封面重试）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.load_env import load_env

load_env(ROOT)


def _format_result(out: dict) -> str:
    if out.get("status") == "success":
        data = out.get("data") or {}
        lines = [
            out.get("summary") or "成功",
            f"media_id: {data.get('media_id', '')}",
            f"operation: {data.get('operation', '')}",
        ]
        if data.get("thumb_omitted_invalid"):
            lines.append("说明: 封面 media_id 无效已自动省略，请在微信后台补封面。")
        if data.get("message"):
            lines.append(f"detail: {data['message']}")
        return "\n".join(lines)
    err = out.get("error") or {}
    return json.dumps(
        {
            "ok": False,
            "summary": out.get("summary"),
            "code": err.get("code"),
            "message": err.get("message"),
        },
        ensure_ascii=False,
        indent=2,
    )


def _build_mcp():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "hou_wechat_mp_draft",
        instructions=(
            "将 Markdown 或 HTML 正文写入微信公众号草稿箱（add/update）。"
            "需配置 WECHAT_MP_APP_ID / WECHAT_MP_APP_SECRET。"
        ),
    )

    @mcp.tool()
    async def hou_wechat_mp_draft_publish(
        operation: str = "add",
        article_markdown: str = "",
        article_html: str = "",
        title: str = "",
        digest: str = "",
        author: str = "",
        thumb_media_id: str = "",
        media_id: str = "",
        content_source_url: str = "",
    ) -> str:
        """新建或更新公众号图文草稿。正文用 article_markdown 或 article_html（HTML 优先）。"""
        from backend.infrastructure.execution.task_handlers import (
            process_wechat_mp_draft_task,
            validate_task_creation,
        )
        from backend.services.wechat_mp_service.article_markdown_html import (
            article_markdown_to_wechat_html,
            digest_clamp,
            title_from_first_atx_heading,
        )

        op = (operation or "add").strip().lower()
        if op not in ("add", "update"):
            return _format_result(
                {
                    "status": "error",
                    "summary": "operation 须为 add 或 update",
                    "error": {"code": "BAD_OPERATION", "message": operation},
                }
            )

        html = (article_html or "").strip()
        md = (article_markdown or "").strip()
        if html:
            content = html
        elif md:
            content = article_markdown_to_wechat_html(md)
        else:
            return _format_result(
                {
                    "status": "error",
                    "summary": "缺少正文",
                    "error": {"code": "MISSING_BODY", "message": "请提供 article_markdown 或 article_html"},
                }
            )

        tit = (title or "").strip()
        if not tit and md:
            tit = title_from_first_atx_heading(md)

        metadata: dict = {
            "operation": op,
            "title": tit,
            "content": content,
            "digest": digest_clamp(digest) or "",
            "author": (author or "").strip(),
            "thumb_media_id": (thumb_media_id or "").strip(),
            "content_source_url": (content_source_url or "").strip(),
            "media_id": (media_id or "").strip(),
        }
        # 空串与任务校验一致：不传无意义字段
        if not metadata["digest"]:
            metadata.pop("digest", None)
        if not metadata["author"]:
            metadata.pop("author", None)
        if not metadata["thumb_media_id"]:
            metadata.pop("thumb_media_id", None)
        if not metadata["content_source_url"]:
            metadata.pop("content_source_url", None)
        if op == "add":
            metadata.pop("media_id", None)
        else:
            if not metadata.get("media_id"):
                return _format_result(
                    {
                        "status": "error",
                        "summary": "update 须提供 media_id",
                        "error": {"code": "MISSING_MEDIA_ID", "message": "请在微信草稿列表取得待更新草稿的 media_id"},
                    }
                )

        ok, verr = validate_task_creation("wechat_mp_draft", metadata)
        if not ok:
            return _format_result(
                {
                    "status": "error",
                    "summary": verr or "参数校验失败",
                    "error": {"code": "VALIDATION", "message": verr or ""},
                }
            )

        out = await process_wechat_mp_draft_task(
            {"task_id": "mcp-wechat-mp-draft", "metadata": metadata}
        )
        return _format_result(out)

    return mcp


def main() -> None:
    os.environ.setdefault("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", "true")
    mcp = _build_mcp()
    mcp.run()


if __name__ == "__main__":
    main()
