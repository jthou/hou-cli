# 时间：2026-04-11；理由：MCP/CLI 需与 Web 一致将 Markdown 正文转为公众号 API 所需 HTML；方法：markdown 库 + section 包裹（与脚本 rewrite 风格接近）
"""公众号草稿正文：Markdown → HTML（供 MCP、脚本调用；复杂公式/上传图仍以 Web 任务为准）。"""
from __future__ import annotations

import re
from typing import Optional

import markdown


def title_from_first_atx_heading(md: str, max_len: int = 64) -> str:
    """取正文首行 ATX 标题 `# 标题` 作为建议标题；无则空字符串。"""
    for line in (md or "").splitlines():
        s = line.strip()
        if s.startswith("#"):
            t = re.sub(r"^#+\s*", "", s).strip()
            return (t[:max_len] if t else "")[:max_len]
    return ""


def article_markdown_to_wechat_html(md: str) -> str:
    """
    将 Markdown 转为可提交 `wechat_mp_draft` 的 HTML 片段。
    使用 fenced_code、tables、extra；外层 section 便于在微信侧识别来源。
    """
    text = (md or "").strip()
    if not text:
        return ""
    body = markdown.markdown(
        text,
        extensions=["extra", "nl2br", "tables", "fenced_code"],
    )
    return (
        '<section data-hou-cli="wechat-draft" '
        'style="color:#24292f;font-size:16px;line-height:1.62;">'
        f"{body}"
        "</section>"
    )


def digest_clamp(s: Optional[str], max_len: int = 120) -> Optional[str]:
    t = (s or "").strip()
    if not t:
        return None
    return t[:max_len] if len(t) > max_len else t
