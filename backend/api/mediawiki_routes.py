"""MediaWiki 相关路由"""
import asyncio
import hashlib
import os
import re
import random
import tempfile
from typing import Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse, unquote, urlunparse

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.services.mediawiki_client_service import (
    MediaWikiClientService,
    MediaWikiSyncService,
)
from shared.debug_utils import debug_log
from shared.httpx_defaults import httpx_default_network_kwargs

router = APIRouter()


def _parse_via_http(wikitext: str, title: Optional[str] = None) -> str:
    """直接 HTTP 请求 MediaWiki parse API，无需 mwclient 连接。"""
    base = (os.getenv("MEDIAWIKI_URL") or "").rstrip("/")
    if not base:
        raise ValueError("MEDIAWIKI_URL 未配置")
    api_url = urljoin(base + "/", "api.php")
    params = {
        "action": "parse",
        "text": wikitext,
        "contentmodel": "wikitext",
        "prop": "text",
        "format": "json",
    }
    if title:
        params["title"] = title
    r = httpx.post(api_url, data=params, timeout=30.0, **httpx_default_network_kwargs())
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data.get("error", {}).get("info", "Unknown API error"))
    parsed = data.get("parse", {})
    text_data = parsed.get("text", {})
    html = text_data.get("*", "")
    if not html:
        raise ValueError("Parse API returned empty HTML")
    return html


def _make_wiki_links_absolute(html: str, base_url: str) -> str:
    """将 parse 返回的 HTML 中相对 wiki 链接转为绝对 URL，便于预览时正确跳转。"""
    if not base_url or not html:
        return html
    base = base_url.rstrip("/")
    # href="/index.php/Page" 或 href="/wiki/Page" → href="base/index.php/Page"
    html = re.sub(r'href="/index\.php/', f'href="{base}/index.php/', html)
    html = re.sub(r'href="/wiki/', f'href="{base}/wiki/', html)
    return html


def _get_mediawiki_base_url() -> str:
    """获取 MediaWiki 基础 URL（无末尾斜杠）"""
    return (os.getenv("MEDIAWIKI_URL") or "http://www.jthou.com/mediawiki").rstrip("/")


def _image_fetch_replace_host_set() -> Optional[set[str]]:
    """
    允许用 MEDIAWIKI_FETCH_REPLACE_ORIGIN 改写的图片 URL host（小写）。
    若设置 MEDIAWIKI_FETCH_REPLACE_FOR_HOSTS（逗号分隔），仅匹配列表；
    否则使用 MEDIAWIKI_URL 的 host 及其 www. / 裸域 变体（避免 jthou.com 与 www.jthou.com 不一致导致不重写）。
    """
    raw = (os.getenv("MEDIAWIKI_FETCH_REPLACE_FOR_HOSTS") or "").strip()
    if raw:
        return {h.strip().lower() for h in raw.split(",") if h.strip()}
    wiki_h = (urlparse(_get_mediawiki_base_url()).hostname or "").lower()
    if not wiki_h:
        return None
    s = {wiki_h}
    if wiki_h.startswith("www."):
        root = wiki_h[4:]
        if root:
            s.add(root)
    else:
        s.add("www." + wiki_h)
    return s


def _url_for_server_side_image_fetch(url: str) -> str:
    """
    服务端拉取「与 Wiki 同 host」的图片 URL（如 /images/...）时，走公网域名经反代易出现 502。
    可选：在 .env 设置 MEDIAWIKI_FETCH_REPLACE_ORIGIN（如 http://127.0.0.1），当 image URL 的 host
    属于 _image_fetch_replace_host_set() 时替换 scheme+host，保留 path/query。
    """
    replace = (os.getenv("MEDIAWIKI_FETCH_REPLACE_ORIGIN") or "").strip().rstrip("/")
    if not replace:
        return url
    try:
        u = urlparse(url)
        img_h = (u.hostname or "").lower()
        allowed = _image_fetch_replace_host_set()
        if not allowed or img_h not in allowed:
            return url
        raw = replace if "://" in replace else f"http://{replace}"
        ru = urlparse(raw)
        if not ru.scheme or not ru.netloc:
            return url
        return urlunparse((ru.scheme, ru.netloc, u.path or "", u.params, u.query, u.fragment))
    except Exception:
        return url


# 部分反代对 Python/httpx 默认 UA 返回异常；与浏览器行为对齐以提高兼容性
_IMAGE_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


async def _httpx_get_one_url(fetch_url: str) -> Tuple[bytes, str]:
    """GET 单 URL；对 502/503/504 与连接错误最多重试 2 次。"""
    transient_status = {502, 503, 504}
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=30.0, **httpx_default_network_kwargs()
            ) as client:
                resp = await client.get(fetch_url, headers=_IMAGE_FETCH_HEADERS)
                resp.raise_for_status()
                return (resp.content, resp.headers.get("content-type", ""))
        except httpx.HTTPStatusError as e:
            if e.response.status_code in transient_status and attempt < 2:
                await asyncio.sleep(0.6 * (attempt + 1))
                continue
            raise
        except httpx.RequestError:
            if attempt < 2:
                await asyncio.sleep(0.6 * (attempt + 1))
                continue
            raise
    raise RuntimeError("_httpx_get_one_url: unreachable")


async def _httpx_get_image_bytes(url: str) -> Tuple[bytes, str]:
    """先按改写 URL（若有）拉取；若仍 502/503/504 则回退原始 URL（含浏览器 UA）。"""
    fetch_url = _url_for_server_side_image_fetch(url)
    transient = {502, 503, 504}
    try:
        return await _httpx_get_one_url(fetch_url)
    except httpx.HTTPStatusError as e:
        if fetch_url != url and e.response.status_code in transient:
            return await _httpx_get_one_url(url)
        raise


def _search_via_http(query: str, limit: int = 20) -> list[dict]:
    """直接 HTTP 请求 MediaWiki search API，无需 mwclient。用于公开 Wiki 或 mwclient 失败时回退。"""
    base = (os.getenv("MEDIAWIKI_URL") or "").rstrip("/")
    if not base:
        raise ValueError("MEDIAWIKI_URL 未配置")
    api_url = urljoin(base + "/", "api.php")
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": min(limit, 100),
        "srprop": "size|wordcount|snippet|timestamp",
        "format": "json",
    }
    r = httpx.get(api_url, params=params, timeout=15.0, **httpx_default_network_kwargs())
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise ValueError(data.get("error", {}).get("info", "Search API error"))
    items = data.get("query", {}).get("search", [])
    base_url = base.rstrip("/")
    results = []
    for i, hit in enumerate(items):
        title = hit.get("title", "")
        results.append({
            "title": title,
            "snippet": hit.get("snippet", ""),
            "url": f"{base_url}/index.php/{title.replace(' ', '_')}",
            "score": 1.0 / (i + 1),  # 排名分数：第 1 名 1.0，第 2 名 0.5，…
        })
    return results


class MediaWikiEditRequest(BaseModel):
    """MediaWiki 编辑请求"""
    content: str
    summary: Optional[str] = ""


class MediaWikiParseRequest(BaseModel):
    """MediaWiki parse 请求：wikitext 转 HTML 预览"""
    wikitext: str
    title: Optional[str] = None


class MediaWikiUploadImageRequest(BaseModel):
    """网页阅读：从图片 URL 上传到 MediaWiki，返回 [[File:xxx]] 格式"""
    image_url: str


@router.get("/mediawiki/diagnostic")
async def mediawiki_diagnostic():
    """诊断 MediaWiki 配置（不输出敏感值），用于排查 readapidenied"""
    import os
    return {
        "url_set": bool((os.getenv("MEDIAWIKI_URL") or "").strip()),
        "fetch_replace_origin_set": bool((os.getenv("MEDIAWIKI_FETCH_REPLACE_ORIGIN") or "").strip()),
        "fetch_replace_for_hosts_custom": bool((os.getenv("MEDIAWIKI_FETCH_REPLACE_FOR_HOSTS") or "").strip()),
        "username_set": bool((os.getenv("MEDIAWIKI_USERNAME") or "").strip()),
        "bot_name_set": bool((os.getenv("MEDIAWIKI_BOT_NAME") or "").strip()),
        "password_set": bool((os.getenv("MEDIAWIKI_PASSWORD") or "").strip()),
        "bot_password_set": bool((os.getenv("MEDIAWIKI_BOT_PASSWORD") or "").strip()),
        "has_auth": bool((os.getenv("MEDIAWIKI_BOT_NAME") or os.getenv("MEDIAWIKI_USERNAME") or "").strip()),
    }


@router.get("/mediawiki/test-connection")
async def mediawiki_test_connection():
    """测试 MediaWiki 连接与读权限。新建 client 连接并调用 query，用于排查 readapidenied。"""
    try:
        client = MediaWikiClientService()
        client.connect()
        ok, msg = client.verify_read_access()
        return {"success": ok, "message": msg}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/mediawiki/reset-client")
async def mediawiki_reset_client():
    """重置 MediaWiki 客户端单例。修改 .env 后调用此接口，下次请求会重新连接。"""
    global _mediawiki_client, _mediawiki_sync_service
    _mediawiki_client = None
    _mediawiki_sync_service = None
    return {"success": True, "message": "Client reset. Next request will reconnect."}


@router.get("/mediawiki/base-url")
async def mediawiki_base_url():
    """返回 MediaWiki 基础 URL，供前端将 [[xxx]] 解析为可点击链接。"""
    return {"base_url": _get_mediawiki_base_url()}


def _parse_and_postprocess(wikitext: str, title: Optional[str] = None) -> tuple[str, str]:
    """解析 wikitext 为 HTML，并将相对链接转为绝对 URL。返回 (html, base_url)。"""
    base_url = _get_mediawiki_base_url()
    # 1. 优先 mwclient（支持私有 Wiki 认证）
    try:
        client = get_mediawiki_client()
        html = client.parse_wikitext(wikitext, title=title)
        return _make_wiki_links_absolute(html, base_url), base_url
    except Exception as e:
        debug_log(f"MediaWiki parse (mwclient) failed: {str(e)}", level="warning")

    # 2. 回退：直接 HTTP（公开 Wiki 无需认证）
    html = _parse_via_http(wikitext, title=title)
    return _make_wiki_links_absolute(html, base_url), base_url


@router.post("/mediawiki/parse")
async def parse_mediawiki_wikitext(request: MediaWikiParseRequest):
    """将 wikitext 解析为 HTML，用于预览。[[xxx]] 等链接会解析为绝对 URL 便于点击。"""
    wikitext = (request.wikitext or "").strip()
    if not wikitext:
        return {"success": True, "html": "", "base_url": _get_mediawiki_base_url()}

    try:
        html, base_url = _parse_and_postprocess(wikitext, title=request.title)
        return {"success": True, "html": html, "base_url": base_url}
    except Exception as e:
        debug_log(f"MediaWiki parse failed: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")


def _wiki_filename_from_special_filepath_url(url: str, wiki_base_raw: str) -> Optional[str]:
    """
    若 image_url 已是本站「图片展示」链接（Special:FilePath/文件名），则不应再用 httpx 去拉取：
    本站 nginx/PHP 常对 FilePath 返回 502，且文件已在 Wiki 上，无需重复上传。
    时间：2026-03-24
    """
    try:
        u = urlparse((url or "").strip())
        base = urlparse((wiki_base_raw or "").strip().rstrip("/"))
        if not u.scheme or not base.scheme:
            return None
        if u.scheme.lower() != base.scheme.lower():
            return None
        if (u.netloc or "").lower() != (base.netloc or "").lower():
            return None
        base_path = (base.path or "").rstrip("/")
        full_path = unquote(u.path or "")
        if base_path and base_path != "/":
            if not (full_path == base_path or full_path.startswith(base_path + "/")):
                return None
        marker = "/Special:FilePath/"
        name: Optional[str] = None
        if marker in full_path:
            tail = full_path.split(marker, 1)[-1].strip("/")
            tail = tail.split("?")[0].split("#")[0]
            if tail and "/" not in tail and ".." not in tail:
                name = tail
        if name is None and u.query:
            for raw_t in parse_qs(u.query).get("title", []):
                t = unquote(raw_t or "")
                if "Special:FilePath/" in t:
                    part = t.split("Special:FilePath/", 1)[-1].strip()
                    part = part.split("?")[0].split("#")[0]
                    if part and "/" not in part and ".." not in part:
                        name = part
                        break
        if not name:
            return None
        return name
    except Exception:
        return None


def _try_read_web_reader_inline_static(url: str) -> Optional[Tuple[bytes, str]]:
    """
    网页阅读配图落在本机 data 目录；upload-image 若用 httpx 拉取自己的公网地址，经 nginx 常 502。
    时间：2026-03-24；方法：识别 /api/web-reader/inline-static/{uuid}.ext 后直读文件（与 web_reader_routes 同目录与校验）。
    """
    try:
        path = (urlparse(url).path or "").rstrip("/")
        prefix = "/api/web-reader/inline-static"
        if not path.startswith(prefix + "/"):
            return None
        fname = path[len(prefix) + 1 :].lstrip("/")
        if not fname or "/" in fname or "\\" in fname:
            return None
        from backend.api.web_reader_routes import _INLINE_IMG_DIR, _SAFE_INLINE_NAME

        if not _SAFE_INLINE_NAME.match(fname):
            return None
        fp = _INLINE_IMG_DIR / fname
        if not fp.is_file():
            return None
        data = fp.read_bytes()
        ext = fname.rsplit(".", 1)[-1].lower()
        ct = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }.get(ext, "application/octet-stream")
        return (data, ct)
    except OSError:
        return None


def _filename_from_url(url: str, content_type: str = "") -> str:
    """从 URL 或 Content-Type 提取安全文件名。时间：2025-03-13；理由：网页图片上传需可预测扩展名；方法：优先 path，回退 mimetype。"""
    parsed = urlparse(url)
    path = unquote(parsed.path or "")
    name = (path.split("/")[-1] or "image").strip()
    # 移除 query 残留
    if "?" in name:
        name = name.split("?")[0]
    # 仅保留安全字符
    safe = re.sub(r"[^\w\-_.]", "_", name)
    if not safe:
        safe = "image"
    # 确保有扩展名
    ext_map = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}
    if "." not in safe and content_type:
        ext = ext_map.get(content_type.split(";")[0].strip().lower(), ".png")
        safe = safe + ext
    return safe or "image.png"


@router.post("/mediawiki/upload-image")
async def upload_image_to_mediawiki(request: MediaWikiUploadImageRequest):
    """
    从图片 URL 下载并上传到 MediaWiki，返回 [[File:xxx]] 格式。
    用于网页阅读：选中网页中的图片，上传后得到 MediaWiki 引用。
    文件名与 upload-image-file 一致：按内容 SHA256 前 16 位命名 img_<hash>.<ext>，避免大量 image.png 撞车。
    """
    url = (request.image_url or "").strip()
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="image_url 必须为 http(s) URL")

    wiki_base = _get_mediawiki_base_url()
    fp_name = _wiki_filename_from_special_filepath_url(url, wiki_base)
    if fp_name:
        wikitext = f"[[File:{fp_name}]]"
        return {"success": True, "filename": fp_name, "wikitext": wikitext}

    try:
        local = _try_read_web_reader_inline_static(url)
        if local:
            content, content_type = local
        else:
            try:
                content, content_type = await _httpx_get_image_bytes(url)
            except httpx.HTTPStatusError as e:
                extra = ""
                if e.response.status_code in (502, 503, 504):
                    extra = (
                        " 已尝试浏览器 User-Agent，并在配置了 REPLACE_ORIGIN 时对原始公网 URL 回退。"
                        " 若 Hou CLI 运行在你的个人电脑而非 Wiki 服务器，请勿设置 MEDIAWIKI_FETCH_REPLACE_ORIGIN，"
                        "否则 http://127.0.0.1/images/... 会打到本机而非站点。"
                        " 同机部署时可设 REPLACE_ORIGIN 为 Nginx 实际监听地址；"
                        " 亦可设 MEDIAWIKI_FETCH_REPLACE_FOR_HOSTS=www.jthou.com,jthou.com 显式限定重写范围。"
                    )
                raise HTTPException(
                    status_code=502 if e.response.status_code == 502 else 500,
                    detail=f"拉取图片失败: HTTP {e.response.status_code}{extra}",
                ) from e

        if not content or len(content) > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=400, detail="图片为空或超过 50MB 限制")

        url_hint = _filename_from_url(url, content_type)
        ext = _ext_from_upload(url_hint, content_type)
        basename = _hashed_upload_basename(content, ext)
        filename = re.sub(r"[^\w.\-]", "_", basename)
        if not filename.lower().endswith(tuple(_ALLOWED_IMG_EXT)):
            filename = _hashed_upload_basename(content, ".png")
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(content)
            tmp_path = f.name

        try:
            mw_client = get_mediawiki_client()
            try:
                mw_client.upload_file(filename, tmp_path, description="", ignore_warnings=True)
            except Exception as up_err:
                err_str = str(up_err).lower()
                if "fileexists-no-change" in err_str or "exact duplicate" in err_str:
                    pass
                else:
                    raise
            wikitext = f"[[File:{filename}]]"
            return {"success": True, "filename": filename, "wikitext": wikitext}
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"MediaWiki upload-image failed: {str(e)}", level="error")
        msg = str(e)
        hint = ""
        if "502" in msg or "503" in msg or "504" in msg:
            hint = (
                " 若图片在 Wiki 同域（如 /images/），可设置 MEDIAWIKI_FETCH_REPLACE_ORIGIN 走本机或内网拉取；"
                "或稍后重试（反代瞬时故障）。"
            )
        raise HTTPException(status_code=500, detail=f"上传失败: {msg}{hint}")


_ALLOWED_IMG_EXT = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})


def _ext_from_upload(filename: str, content_type: Optional[str]) -> str:
    """从原始文件名或 Content-Type 得到小写扩展名（含点）。"""
    name = (filename or "").strip()
    if "." in name:
        ext = "." + name.rsplit(".", 1)[-1].lower()
        if ext == ".jpeg":
            ext = ".jpg"
        if ext in _ALLOWED_IMG_EXT:
            return ext
    ct = (content_type or "").split(";")[0].strip().lower()
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }.get(ct, ".png")


def _hashed_upload_basename(content: bytes, ext: str) -> str:
    """内容 SHA256 前 16 位 + 扩展名，降低与 Wiki 上已有文件重名概率。"""
    h = hashlib.sha256(content).hexdigest()[:16]
    e = ext if ext in _ALLOWED_IMG_EXT else ".png"
    return f"img_{h}{e}"


@router.post("/mediawiki/upload-image-file")
async def upload_image_file_to_mediawiki(file: UploadFile = File(...)):
    """
    剪贴板/本地图片 multipart 上传至 MediaWiki。
    时间：2026-03-13；理由：编辑框粘贴图片需直传 Wiki；方法：内容哈希命名 img_<sha256[:16]>.<ext>，临时文件 upload_file。
    """
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取文件失败: {e}") from e

    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片超过 50MB 限制")

    ext = _ext_from_upload(file.filename or "", file.content_type)
    basename = _hashed_upload_basename(content, ext)
    filename = re.sub(r"[^\w.\-]", "_", basename)
    if not filename.lower().endswith(tuple(_ALLOWED_IMG_EXT)):
        filename = _hashed_upload_basename(content, ".png")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
            f.write(content)
            tmp_path = f.name
        mw_client = get_mediawiki_client()
        try:
            mw_client.upload_file(filename, tmp_path, description="", ignore_warnings=True)
        except Exception as up_err:
            err_str = str(up_err).lower()
            if "fileexists-no-change" in err_str or "exact duplicate" in err_str:
                pass
            else:
                raise
        wikitext = f"[[File:{filename}]]"
        return {"success": True, "filename": filename, "wikitext": wikitext}
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"MediaWiki upload-image-file failed: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}") from e
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# 延迟创建服务实例
_mediawiki_client = None
_mediawiki_sync_service = None


def get_mediawiki_client():
    """获取 MediaWiki 客户端实例（单例模式）"""
    global _mediawiki_client
    if _mediawiki_client is None:
        try:
            _mediawiki_client = MediaWikiClientService()
            _mediawiki_client.connect()
        except Exception as e:
            debug_log(
                f"Failed to initialize MediaWiki client: {str(e)}",
                level="error"
            )
            raise
    return _mediawiki_client

def get_mediawiki_sync_service():
    """获取 MediaWiki 同步服务实例（单例模式）"""
    global _mediawiki_sync_service
    if _mediawiki_sync_service is None:
        try:
            client = get_mediawiki_client()
            _mediawiki_sync_service = MediaWikiSyncService(client=client)
        except Exception as e:
            debug_log(
                f"Failed to initialize MediaWiki sync service: {str(e)}",
                level="error"
            )
            raise
    return _mediawiki_sync_service


@router.get("/mediawiki/search")
async def search_mediawiki(
    query: str,
    limit: int = 20,
):
    """搜索 MediaWiki 页面。优先 mwclient（带认证），失败时尝试直接 HTTP（公开 Wiki）。"""
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="limit must be between 1 and 100"
            )
        q = (query or "").strip()
        if not q:
            return {"success": True, "count": 0, "results": [], "totalhits": None}

        # 1. 优先 mwclient（支持私有 Wiki 认证）
        try:
            client = get_mediawiki_client()
            results = client.search_pages(q, limit=limit)
            out = [
                {"title": r.title, "snippet": r.snippet, "url": r.url, "score": r.score}
                for r in results
            ]
            return {"success": True, "count": len(out), "results": out, "totalhits": None}
        except Exception as e:
            debug_log(f"MediaWiki search (mwclient) failed: {str(e)}", level="warning")

        # 2. 回退：直接 HTTP（公开 Wiki 无需认证）
        raw = _search_via_http(q, limit=limit)
        out = [{"title": r["title"], "snippet": r["snippet"], "url": r["url"], "score": r["score"]} for r in raw]
        return {"success": True, "count": len(out), "results": out, "totalhits": None}
    except HTTPException:
        raise
    except ValueError as e:
        debug_log(f"MediaWiki search failed: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        debug_log(f"MediaWiki search failed: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/mediawiki/search-read")
async def search_and_read_mediawiki(
    terms: str,
    per_term_limit: int = 5,
):
    """
    按多个关键词搜索 MediaWiki，并读取每篇页面的完整内容。

    - terms: 用逗号或空格分隔的多个关键词，例如
      "网文抓取, hou-cli, 2026年3月3日, 2026年第10周, 2026年3月"
    - per_term_limit: 每个关键词最多抓取的文章数，默认 5，范围 1–20。
    """
    try:
        raw_terms = terms or ""
        parts = [
            p.strip()
            for p in raw_terms.replace("，", ",").split(",")
            if p.strip()
        ]
        # 允许用户用空格分词；如果只给了一个长串，再按空白拆一层
        if len(parts) == 1:
            parts = [p.strip() for p in raw_terms.split() if p.strip()]

        uniq_terms = []
        seen = set()
        for p in parts:
            if p and p not in seen:
                seen.add(p)
                uniq_terms.append(p)

        if not uniq_terms:
            raise HTTPException(
                status_code=400,
                detail=(
                    "terms 参数解析失败：请提供至少一个非空关键词"
                    "（用逗号或空格分隔）。"
                ),
            )

        try:
            per_term = int(per_term_limit)
        except (TypeError, ValueError):
            per_term = 5
        if per_term < 1:
            per_term = 1
        if per_term > 20:
            per_term = 20

        # 每次请求新建 client，避免单例会话过期导致 readapidenied（2025-03-13）
        client = MediaWikiClientService()
        client.connect()

        results = []
        total_pages = 0

        for term in uniq_terms:
            search_results = client.search_pages(term, limit=per_term)
            pages = []
            for r in search_results:
                page = client.get_page(r.title)
                if not page:
                    continue
                pages.append(
                    {
                        "title": page.title,
                        "url": page.url,
                        "categories": page.categories,
                        "content": page.content,
                    }
                )

            results.append(
                {
                    "term": term,
                    "requested_limit": per_term,
                    "count": len(pages),
                    "pages": pages,
                }
            )
            total_pages += len(pages)

        return {
            "success": True,
            "terms": uniq_terms,
            "per_term_limit": per_term,
            "total_pages": total_pages,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(
            f"MediaWiki search-read failed: {str(e)}",
            level="error",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Search-read failed: {str(e)}",
        )


@router.get("/mediawiki/recent-read")
async def recent_read_mediawiki(
    count: int = 10,
):
    """
    获取最近修改的 n 篇 MediaWiki 文章的完整内容。

    - count: 文章数量，默认 10，范围 1–50。
    """
    try:
        try:
            n = int(count)
        except (TypeError, ValueError):
            n = 10
        if n < 1:
            n = 1
        if n > 50:
            n = 50

        client = get_mediawiki_client()
        titles = client.get_recently_changed_pages(limit=n, namespace=0)
        if not titles:
            raise HTTPException(
                status_code=404,
                detail="MediaWiki 中暂无最近修改的页面。",
            )

        pages = []
        for title in titles:
            page = client.get_page(title)
            if not page:
                continue
            pages.append(
                {
                    "title": page.title,
                    "url": page.url,
                    "categories": page.categories,
                    "content": page.content,
                }
            )

        results = [
            {
                "term": "最新更改",
                "requested_limit": n,
                "count": len(pages),
                "pages": pages,
            }
        ]

        return {
            "success": True,
            "terms": ["最新更改"],
            "per_term_limit": n,
            "total_pages": len(pages),
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(
            f"MediaWiki recent-read failed: {str(e)}",
            level="error",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Recent-read failed: {str(e)}",
        )


@router.get("/mediawiki/random-read")
async def random_read_mediawiki(
    count: int = 5,
):
    """
    随机抓取若干篇 MediaWiki 文章的完整内容。

    - count: 随机抓取的文章数量，默认 5，范围 1–50。
    """
    try:
        try:
            n = int(count)
        except (TypeError, ValueError):
            n = 5
        if n < 1:
            n = 1
        if n > 50:
            n = 50

        client = get_mediawiki_client()
        titles = client.get_all_pages(namespace=0, limit=None)
        total_titles = len(titles)
        if total_titles == 0:
            raise HTTPException(
                status_code=404,
                detail="MediaWiki 中暂无页面可供随机抓取。",
            )

        if n >= total_titles:
            sample_titles = titles
        else:
            sample_titles = random.sample(titles, n)

        pages = []
        for title in sample_titles:
            page = client.get_page(title)
            if not page:
                continue
            pages.append(
                {
                    "title": page.title,
                    "url": page.url,
                    "categories": page.categories,
                    "content": page.content,
                }
            )

        results = [
            {
                "term": "随机",
                "requested_limit": n,
                "count": len(pages),
                "pages": pages,
            }
        ]

        return {
            "success": True,
            "terms": ["随机"],
            "per_term_limit": n,
            "total_pages": len(pages),
            "wiki_total_titles": total_titles,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(
            f"MediaWiki random-read failed: {str(e)}",
            level="error",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Random-read failed: {str(e)}",
        )

@router.get("/mediawiki/pages/{title:path}")
async def get_mediawiki_page(title: str):
    """获取 MediaWiki 页面
    
    Args:
        title: 页面标题（URL 编码）
        
    Returns:
        页面内容
    """
    try:
        client = get_mediawiki_client()
        page = client.get_page(title)
        
        if not page:
            raise HTTPException(
                status_code=404,
                detail=f"Page '{title}' not found"
            )
        
        return {
            "success": True,
            "page": {
                "title": page.title,
                "content": page.content,
                "url": page.url,
                "categories": page.categories,
                "links": page.links,
                "last_modified": page.last_modified.isoformat(),
                "revision_id": page.revision_id
            }
        }
    except HTTPException:
        # 重新抛出 HTTPException（如404错误）
        raise
    except Exception as e:
        debug_log(
            f"Get MediaWiki page failed: {str(e)}",
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get page: {str(e)}"
        )

@router.post("/mediawiki/pages/{title:path}")
async def edit_mediawiki_page(title: str, request: MediaWikiEditRequest):
    """编辑 MediaWiki 页面
    
    Args:
        title: 页面标题（URL 编码）
        request: 编辑请求（包含 content 和 summary）
        
    Returns:
        编辑结果
    """
    try:
        client = get_mediawiki_client()
        success = client.edit_page(
            title,
            request.content,
            summary=request.summary or "由 API 编辑"
        )
        
        if success:
            return {
                "success": True,
                "message": f"Page '{title}' edited successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Edit failed"
            )
    except Exception as e:
        debug_log(
            f"Edit MediaWiki page failed: {str(e)}",
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Edit failed: {str(e)}"
        )

@router.post("/mediawiki/sync")
async def trigger_sync(
    force: bool = False,
    category: Optional[str] = None
):
    """触发 MediaWiki 同步
    
    Args:
        force: 是否强制全量同步
        category: 同步指定分类（可选）
        
    Returns:
        同步结果
    """
    try:
        sync_service = get_mediawiki_sync_service()
        
        if category:
            result = sync_service.sync_category(category, force=force)
        else:
            result = sync_service.sync_all_pages(force=force)
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        debug_log(
            f"MediaWiki sync failed: {str(e)}",
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )

@router.get("/mediawiki/sync/status")
async def get_sync_status():
    """获取同步状态
    
    Returns:
        同步状态信息
    """
    try:
        sync_service = get_mediawiki_sync_service()
        status = sync_service.get_sync_status()
        
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        debug_log(
            f"Get sync status failed: {str(e)}",
            level="error"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync status: {str(e)}"
        )

