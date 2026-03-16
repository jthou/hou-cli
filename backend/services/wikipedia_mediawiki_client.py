"""
Wikipedia MediaWiki API 客户端（直接 HTTP 调用，无需认证）。
Wikipedia 与 MediaWiki 使用相同 API 接口。
"""
import logging
from typing import List, Optional
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

# Wikipedia API 要求必须设置 User-Agent，否则返回 403
WIKIPEDIA_USER_AGENT = "HouCLI-WikipediaReader/1.0 (https://github.com/jthou/hou-cli; contact@example.com)"

# 各语言 Wikipedia API 基础 URL
WIKIPEDIA_API_BASE = {
    "zh": "https://zh.wikipedia.org/w/api.php",
    "en": "https://en.wikipedia.org/w/api.php",
}


def _get_api_url(lang: str = "zh") -> str:
    return WIKIPEDIA_API_BASE.get(lang, WIKIPEDIA_API_BASE["zh"])


def _get_base_url(lang: str = "zh") -> str:
    """获取 Wikipedia 站点基础 URL（用于链接拼接）"""
    if lang == "en":
        return "https://en.wikipedia.org"
    return "https://zh.wikipedia.org"


def search_pages(
    query: str,
    limit: int = 20,
    lang: str = "zh",
) -> List[dict]:
    """
    搜索 Wikipedia 页面。
    返回 [{"title", "snippet", "url", "score"}, ...]
    """
    api_url = _get_api_url(lang)
    base_url = _get_base_url(lang)
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": min(limit, 100),
        "srprop": "size|wordcount|snippet|timestamp",
        "format": "json",
    }
    r = httpx.get(api_url, params=params, timeout=15.0, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data.get("error", {}).get("info", "Search API error"))
    items = data.get("query", {}).get("search", [])
    results = []
    for i, hit in enumerate(items):
        title = hit.get("title", "")
        results.append({
            "title": title,
            "snippet": hit.get("snippet", ""),
            "url": f"{base_url}/wiki/{title.replace(' ', '_')}",
            "score": 1.0 / (i + 1),
        })
    return results


def get_page_content(title: str, lang: str = "zh") -> Optional[dict]:
    """
    获取页面 wikitext 内容。
    返回 {"title", "content", "url", "categories"} 或 None。
    """
    api_url = _get_api_url(lang)
    base_url = _get_base_url(lang)
    params = {
        "action": "query",
        "prop": "revisions|categories",
        "titles": title,
        "rvprop": "content",
        "format": "json",
    }
    r = httpx.get(api_url, params=params, timeout=15.0, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data.get("error", {}).get("info", "Query API error"))
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None
    page_id = next(iter(pages.keys()))
    page_data = pages[page_id]
    if page_id == "-1" or "missing" in page_data:
        return None
    revs = page_data.get("revisions", [])
    content = ""
    if revs:
        # rvprop=content 时内容在 revs[0]["*"]；新版 API 可能在 slots.main["*"]
        rev = revs[0]
        if "*" in rev:
            content = rev["*"]
        else:
            slots = rev.get("slots", {})
            main = slots.get("main", {})
            content = main.get("*", "")
    cats = page_data.get("categories", [])
    categories = [c.get("title", "").replace("Category:", "") for c in cats]
    return {
        "title": page_data.get("title", title),
        "content": content,
        "url": f"{base_url}/wiki/{page_data.get('title', title).replace(' ', '_')}",
        "categories": categories,
    }


def parse_wikitext(wikitext: str, title: Optional[str] = None, lang: str = "zh") -> str:
    """
    使用 Wikipedia parse API 将 wikitext 转为 HTML。
    """
    api_url = _get_api_url(lang)
    params = {
        "action": "parse",
        "text": wikitext,
        "contentmodel": "wikitext",
        "prop": "text",
        "format": "json",
    }
    if title:
        params["title"] = title
    r = httpx.post(api_url, data=params, timeout=30.0, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data.get("error", {}).get("info", "Parse API error"))
    parsed = data.get("parse", {})
    text_data = parsed.get("text", {})
    html = text_data.get("*", "")
    if not html:
        raise ValueError("Parse API returned empty HTML")
    return html


def get_random_titles(limit: int = 5, lang: str = "zh") -> List[str]:
    """获取随机页面标题列表。"""
    api_url = _get_api_url(lang)
    params = {
        "action": "query",
        "list": "random",
        "rnnamespace": "0",
        "rnlimit": min(limit, 20),
        "format": "json",
    }
    r = httpx.get(api_url, params=params, timeout=15.0, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data.get("error", {}).get("info", "Random API error"))
    items = data.get("query", {}).get("random", [])
    return [item.get("title", "") for item in items if item.get("title")]


def get_recently_changed_titles(limit: int = 10, lang: str = "zh") -> List[str]:
    """获取最近修改的页面标题列表。"""
    api_url = _get_api_url(lang)
    params = {
        "action": "query",
        "list": "recentchanges",
        "rcnamespace": "0",
        "rclimit": min(limit, 50),
        "rcprop": "title",
        "format": "json",
    }
    r = httpx.get(api_url, params=params, timeout=15.0, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data.get("error", {}).get("info", "RecentChanges API error"))
    items = data.get("query", {}).get("recentchanges", [])
    seen = set()
    titles = []
    for item in items:
        t = item.get("title", "")
        if t and t not in seen:
            seen.add(t)
            titles.append(t)
    return titles[:limit]
