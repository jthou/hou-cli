"""Web Fetch 工具：抓取 URL 正文，供「URL → 翻译 → 写入 Wiki」等流程使用。

支持：
- URL 校验（仅 http/https）
- 正文提取（优先 trafilatura，回退到简单 HTML 清洗）
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx

from backend.core.agent.tools.base import Tool, ToolParameter, ToolResult

logger = logging.getLogger(__name__)

# 单次抓取超时（秒）
FETCH_TIMEOUT = 30.0

# 危险协议
FORBIDDEN_SCHEMES = ("file", "javascript", "data", "ftp")

# 请求头：模拟浏览器，降低知乎等站点 403 概率
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _validate_url(url: str) -> Optional[str]:
    """校验 URL，合法返回 None，否则返回错误信息。"""
    if not url or not isinstance(url, str):
        return "URL 不能为空"
    url = url.strip()
    if len(url) > 2048:
        return "URL 过长"
    try:
        parsed = urlparse(url)
    except Exception:
        return "URL 格式无效"
    if not parsed.scheme:
        return "请使用完整的 URL（包含 http:// 或 https://）"
    if parsed.scheme.lower() in FORBIDDEN_SCHEMES:
        return f"不允许的协议: {parsed.scheme}"
    if parsed.scheme.lower() not in ("http", "https"):
        return f"仅支持 http/https，当前为 {parsed.scheme}"
    return None


def _extract_with_trafilatura(html: str, url: str) -> Optional[tuple[str, str]]:
    """若已安装 trafilatura，提取 (title, text)。否则返回 None。"""
    try:
        import trafilatura
        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            output_format="txt",
        )
        if not extracted:
            return None
        meta = trafilatura.extract_metadata(html)
        t = getattr(meta, "title", None) if meta else None
        t = (str(t).strip() if t else None)
        return (t, extracted)
    except Exception as e:
        logger.debug("trafilatura 提取失败: %s", e)
        return None


def _extract_title_regex(html: str) -> Optional[str]:
    m = re.search(r"<title[^>]*>\s*([^<]+?)\s*</title>", html, re.I | re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip() or None
    return None


def _strip_tags(html: str) -> str:
    """简单去除 HTML 标签并规范化空白。"""
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.I | re.DOTALL)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.I | re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html).strip()
    return html


def _extract_fallback(html: str) -> tuple[Optional[str], str]:
    """无 trafilatura 时的回退：取 title + 全文 strip 标签。"""
    title = _extract_title_regex(html)
    body = _strip_tags(html)
    return (title, body if body else "")


def _url_to_fallback_title(url: str) -> str:
    """从 URL path 最后一段生成备用标题。"""
    parsed = urlparse(url.strip())
    path = (parsed.path or "").strip("/")
    if not path:
        return parsed.netloc or "Untitled"
    return path.split("/")[-1].replace("-", " ").replace("_", " ") or "Untitled"


class WebFetchTool(Tool):
    """抓取指定 URL 的页面正文与标题，用于翻译、写入 Wiki 等。"""

    def __init__(self):
        parameters = [
            ToolParameter(
                name="url",
                type="string",
                description="要抓取的文章或页面完整 URL（仅支持 http/https）",
                required=True,
            ),
            ToolParameter(
                name="output_format",
                type="string",
                description="输出格式：'text' 或 'markdown'，默认 'text'",
                required=False,
                enum=["text", "markdown"],
            ),
        ]
        super().__init__(
            name="web_fetch",
            description=(
                "抓取指定 URL 的网页正文和标题，用于后续翻译或写入 MediaWiki。"
                "\n使用场景："
                "- 用户要求「把某链接内容翻译成中文并存到 Wiki」时，先调用本工具获取正文和标题"
                "- 需要获取某篇文章的原文内容时"
                "\n返回：title（页面标题，可作为 Wiki 页面名）、content（正文）、content_length。"
                "\n注意：仅支持 http/https。"
            ),
            parameters=parameters,
        )

    def execute(self, **kwargs) -> ToolResult:
        url = (kwargs.get("url") or "").strip()
        output_format = (kwargs.get("output_format") or "text").strip().lower()
        if output_format not in ("text", "markdown"):
            output_format = "text"

        err = _validate_url(url)
        if err:
            return ToolResult(success=False, error=err)

        try:
            with httpx.Client(
                timeout=FETCH_TIMEOUT,
                follow_redirects=True,
                headers=DEFAULT_HEADERS,
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPStatusError as e:
            logger.warning("web_fetch HTTP 错误: %s", e)
            return ToolResult(
                success=False,
                error=f"请求失败: HTTP {e.response.status_code}",
            )
        except httpx.RequestError as e:
            logger.warning("web_fetch 请求错误: %s", e)
            return ToolResult(
                success=False,
                error="网络请求失败，请检查 URL 或稍后重试",
            )

        if not html:
            return ToolResult(success=False, error="页面内容为空")

        extracted = _extract_with_trafilatura(html, url)
        if extracted:
            title, content = extracted
            if not title:
                title = _extract_title_regex(html) or _url_to_fallback_title(url)
        else:
            title, content = _extract_fallback(html)
            if not title:
                title = _url_to_fallback_title(url)

        if not content.strip():
            return ToolResult(success=False, error="未能提取到正文内容")

        if output_format == "markdown":
            content = content.replace("\n\n", "\n\n").strip()

        return ToolResult(
            success=True,
            data={
                "title": title,
                "content": content,
                "content_length": len(content),
                "url": url,
            },
        )
