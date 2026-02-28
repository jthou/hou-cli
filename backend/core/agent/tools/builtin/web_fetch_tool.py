"""Web Fetch 工具：抓取 URL 正文，供「URL → 翻译 → 写入 Wiki」等流程使用。

支持：
- URL 校验（仅 http/https）
- 可选域名白名单（环境变量 WEB_FETCH_ALLOWED_DOMAINS）
- 请求频率限制（默认 ≤10 次/小时，环境变量 WEB_FETCH_RATE_LIMIT_PER_HOUR）
- 并发控制（默认同时最多 5 个请求，环境变量 WEB_FETCH_MAX_CONCURRENT）
- 正文提取（优先 trafilatura，回退到简单 HTML 清洗）
"""

import logging
import os
import re
import threading
import time
from collections import deque
from typing import Optional
from urllib.parse import urlparse

import httpx

from backend.core.agent.tools.base import Tool, ToolParameter, ToolResult

logger = logging.getLogger(__name__)

# 正文最大长度（字符），设计建议 ≤100KB
MAX_CONTENT_LENGTH = 100 * 1024

# 单次抓取超时（秒）
FETCH_TIMEOUT = 30.0

# 危险协议
FORBIDDEN_SCHEMES = ("file", "javascript", "data", "ftp")

# 频率限制：记录最近请求时间戳（进程内）
_rate_limit_timestamps: deque = deque(maxlen=1000)


def _max_concurrent() -> int:
    try:
        return max(1, min(20, int(os.getenv("WEB_FETCH_MAX_CONCURRENT", "5"))))
    except ValueError:
        return 5


# 并发控制：同时最多 N 个抓取请求
_concurrent_semaphore: Optional[threading.Semaphore] = None

# 简单监控计数（进程内，不持久化）
_fetch_success_count = 0
_fetch_failure_count = 0
_fetch_lock = threading.Lock()


def get_web_fetch_stats() -> dict:
    """返回 web_fetch 的简单统计，供监控或管理接口使用。"""
    with _fetch_lock:
        return {
            "success_count": _fetch_success_count,
            "failure_count": _fetch_failure_count,
        }


def _get_semaphore() -> threading.Semaphore:
    global _concurrent_semaphore
    if _concurrent_semaphore is None:
        _concurrent_semaphore = threading.Semaphore(_max_concurrent())
    return _concurrent_semaphore


def _allowed_domains() -> Optional[list[str]]:
    raw = os.getenv("WEB_FETCH_ALLOWED_DOMAINS", "").strip()
    if not raw:
        return None
    return [d.strip().lower() for d in raw.split(",") if d.strip()]


def _rate_limit_per_hour() -> int:
    try:
        return max(1, int(os.getenv("WEB_FETCH_RATE_LIMIT_PER_HOUR", "10")))
    except ValueError:
        return 10


def _check_rate_limit() -> Optional[str]:
    """若超过频率限制返回错误信息，否则返回 None。"""
    per_hour = _rate_limit_per_hour()
    now = time.time()
    one_hour_ago = now - 3600
    global _rate_limit_timestamps
    # 只保留 1 小时内的
    while _rate_limit_timestamps and _rate_limit_timestamps[0] < one_hour_ago:
        _rate_limit_timestamps.popleft()
    if len(_rate_limit_timestamps) >= per_hour:
        return (
            f"请求过于频繁，当前限制为每小时 {per_hour} 次，请稍后再试。"
        )
    _rate_limit_timestamps.append(now)
    return None


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
    domains = _allowed_domains()
    if domains:
        host = (parsed.netloc or "").split(":")[0].lower()
        if not host:
            return "无法解析域名"
        if not any(host == d or host.endswith("." + d) for d in domains):
            return f"域名不在白名单中，当前白名单: {', '.join(domains)}"
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
    # 先去掉 script / style
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.I | re.DOTALL)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.I | re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html).strip()
    return html


def _extract_fallback(html: str) -> tuple[Optional[str], str]:
    """无 trafilatura 时的回退：取 title + 全文 strip 标签。"""
    title = _extract_title_regex(html)
    body = _strip_tags(html)
    return (title, body[:MAX_CONTENT_LENGTH] if body else "")


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
            ToolParameter(
                name="max_length",
                type="integer",
                description="正文最大字符数，默认 100000；超过会截断",
                required=False,
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
                "\n注意：仅支持 http/https；可选配置域名白名单(WEB_FETCH_ALLOWED_DOMAINS)、频率限制(WEB_FETCH_RATE_LIMIT_PER_HOUR)、并发数(WEB_FETCH_MAX_CONCURRENT)。"
            ),
            parameters=parameters,
        )

    def execute(self, **kwargs) -> ToolResult:
        global _fetch_success_count, _fetch_failure_count
        url = (kwargs.get("url") or "").strip()
        output_format = (kwargs.get("output_format") or "text").strip().lower()
        if output_format not in ("text", "markdown"):
            output_format = "text"
        max_length = kwargs.get("max_length")
        if max_length is None:
            max_length = MAX_CONTENT_LENGTH
        else:
            try:
                max_length = max(1000, min(int(max_length), MAX_CONTENT_LENGTH))
            except (TypeError, ValueError):
                max_length = MAX_CONTENT_LENGTH

        err = _validate_url(url)
        if err:
            return ToolResult(success=False, error=err)
        err = _check_rate_limit()
        if err:
            return ToolResult(success=False, error=err)

        sem = _get_semaphore()
        sem.acquire()
        try:
            try:
                with httpx.Client(timeout=FETCH_TIMEOUT, follow_redirects=True) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    html = resp.text
            except httpx.HTTPStatusError as e:
                logger.warning("web_fetch HTTP 错误: %s", e)
                with _fetch_lock:
                    _fetch_failure_count += 1
                return ToolResult(
                    success=False,
                    error=f"请求失败: HTTP {e.response.status_code}",
                )
            except httpx.RequestError as e:
                logger.warning("web_fetch 请求错误: %s", e)
                with _fetch_lock:
                    _fetch_failure_count += 1
                return ToolResult(
                    success=False,
                    error="网络请求失败，请检查 URL 或稍后重试",
                )

            if not html:
                with _fetch_lock:
                    _fetch_failure_count += 1
                return ToolResult(success=False, error="页面内容为空")

            # 优先 trafilatura
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
                with _fetch_lock:
                    _fetch_failure_count += 1
                return ToolResult(success=False, error="未能提取到正文内容")

            content = content[:max_length]
            if output_format == "markdown":
                content = content.replace("\n\n", "\n\n").strip()

            with _fetch_lock:
                _fetch_success_count += 1
            return ToolResult(
                success=True,
                data={
                    "title": title,
                    "content": content,
                    "content_length": len(content),
                    "url": url,
                },
            )
        finally:
            sem.release()
