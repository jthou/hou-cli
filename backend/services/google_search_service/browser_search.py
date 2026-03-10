"""
无头浏览器式网页搜索：通过请求 DuckDuckGo HTML 版获取结果，无需 API Key。
与 Google Custom Search API 返回格式兼容，供 google_search 工具统一使用。
"""
import logging
import time
import re
from typing import List, Optional
from urllib.parse import unquote, urlparse, parse_qs

import requests

from .models import GoogleSearchResult, GoogleSearchResponse

logger = logging.getLogger(__name__)

DDG_HTML_URL = "https://html.duckduckgo.com/html/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class BrowserSearchError(Exception):
    """网页搜索错误"""
    pass


def _decode_duckduckgo_redirect(href: str) -> Optional[str]:
    """从 DuckDuckGo 跳转链接中解析出真实 URL。"""
    if not href or "duckduckgo.com/l/" not in href:
        return href
    try:
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        uddg = qs.get("uddg") or qs.get("uddg")
        if uddg:
            return unquote(uddg[0])
        return href
    except Exception:
        return href


def search(
    query: str,
    num_results: int = 10,
    language: Optional[str] = None,
    timeout: float = 15.0,
) -> GoogleSearchResponse:
    """
    使用 DuckDuckGo HTML 版执行搜索，返回与 GoogleSearchResponse 兼容的结构。
    不依赖 API Key，适合替代 Custom Search API。
    """
    num_results = max(1, num_results)
    start = time.time()
    results: List[GoogleSearchResult] = []

    try:
        resp = requests.post(
            DDG_HTML_URL,
            data={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.HTTPError as e:
        raise BrowserSearchError(f"DuckDuckGo 返回错误: {e.response.status_code}")
    except requests.exceptions.RequestException as e:
        raise BrowserSearchError(f"请求失败: {str(e)}")

    # 解析 HTML：DuckDuckGo HTML 版结果在 div.result 中，链接在 a.result__url
    # 结构: div.result -> h2.result__title -> a; a.result__url; div.result__snippet
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        _parse_fallback(html, query, num_results, results)
        return GoogleSearchResponse(
            results=results,
            total_results=None,
            search_time=time.time() - start,
            query=query,
        )

    soup = BeautifulSoup(html, "html.parser")
    for div in soup.select("div.result")[:num_results]:
        try:
            title_el = div.select_one("h2.result__title a, a.result__a")
            link_el = div.select_one("a.result__url")
            snippet_el = div.select_one("a.result__snippet")

            link = None
            title = ""
            snippet = ""

            if link_el and link_el.get("href"):
                link = _decode_duckduckgo_redirect(link_el["href"])
            if title_el:
                title = (title_el.get_text(strip=True) or "").strip()
                if not link and title_el.get("href"):
                    link = _decode_duckduckgo_redirect(title_el["href"])
            if snippet_el:
                snippet = (snippet_el.get_text(strip=True) or "").strip()

            if not link or "duckduckgo.com/y.js" in link or "ad_domain=" in link:
                continue
            display_link = None
            try:
                display_link = urlparse(link).netloc or link
            except Exception:
                pass
            results.append(
                GoogleSearchResult(
                    title=title or link,
                    link=link,
                    snippet=snippet,
                    display_link=display_link,
                )
            )
        except Exception as e:
            logger.debug("解析单条结果失败: %s", e)
            continue

    return GoogleSearchResponse(
        results=results,
        total_results=None,
        search_time=time.time() - start,
        query=query,
    )


def _parse_fallback(html: str, query: str, num_results: int, results: List[GoogleSearchResult]) -> None:
    """无 BeautifulSoup 时用正则简单提取链接与标题。"""
    # 匹配 DuckDuckGo 跳转链接中的 uddg 真实 URL
    link_re = re.compile(r'href="https?://duckduckgo\.com/l/\?uddg=([^&"]+)[^"]*"', re.I)
    # 匹配类似 <h2 ...><a ...>Title</a> 的标题
    title_re = re.compile(r'<h2[^>]*>.*?<a[^>]*>([^<]+)</a>', re.S | re.I)
    seen = set()
    for m in link_re.finditer(html):
        if len(results) >= num_results:
            break
        try:
            raw_url = m.group(1)
            link = unquote(raw_url.replace("&amp;", "&"))
            if link in seen:
                continue
            seen.add(link)
            display = urlparse(link).netloc if link else ""
            results.append(
                GoogleSearchResult(title=display or link, link=link, snippet="", display_link=display or None)
            )
        except Exception:
            continue
