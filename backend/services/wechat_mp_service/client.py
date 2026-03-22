"""
微信公众号 API 客户端（个人未认证账号可用：token、草稿列表/详情、新增/更新草稿）。
不包含需认证的统计、发布接口。配置：WECHAT_MP_APP_ID、WECHAT_MP_APP_SECRET（.env）。
正文 content 限制：少于 2 万字符、小于 1M（微信接口要求）。
封面上传使用 requests 发 multipart，避免部分环境下 httpx 出现 SSL EOF。
"""
import os
import time
import logging
from typing import Any, Dict, List, Optional

import httpx
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.weixin.qq.com"

# 微信单篇正文限制（与官方文档一致）
CONTENT_MAX_CHARS = 20000
CONTENT_MAX_BYTES = 1024 * 1024  # 1M


class WeChatMPClientError(Exception):
    """微信公众号 API 调用错误"""
    pass


class WeChatMPClient:
    """微信公众号 API 客户端（个人号可用：token、草稿列表/详情；不包含统计与发布）"""

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
    ):
        self.app_id = app_id or os.getenv("WECHAT_MP_APP_ID")
        self.app_secret = app_secret or os.getenv("WECHAT_MP_APP_SECRET")
        if not self.app_id or not self.app_secret:
            raise WeChatMPClientError(
                "请配置 WECHAT_MP_APP_ID 和 WECHAT_MP_APP_SECRET（.env）"
            )
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._token_ttl = 7200  # 2 小时，提前 5 分钟刷新
        self._refresh_before = 300

    def _fetch_token(self, force_refresh: bool = False) -> tuple[str, int]:
        """调用稳定版接口获取 access_token。force_refresh=true 强制刷新（每天限 20 次）。返回 (token, expires_in)。"""
        url = f"{BASE_URL}/cgi-bin/stable_token"
        payload = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
            "force_refresh": force_refresh,
        }
        r = httpx.post(url, json=payload, timeout=15.0)
        r.raise_for_status()
        data = r.json()
        errcode = data.get("errcode")
        if errcode and errcode != 0:
            raise WeChatMPClientError(
                f"获取 token 失败: errcode={errcode}, errmsg={data.get('errmsg', '')}"
            )
        token = data.get("access_token")
        if not token:
            raise WeChatMPClientError("获取 token 返回无 access_token")
        expires_in = data.get("expires_in") or self._token_ttl
        return (token, expires_in)

    def _ensure_token(self, force_refresh: bool = False) -> str:
        """获取并缓存 access_token，使用稳定版接口（getStableAccessToken）避免 40001 invalid credential"""
        now = time.time()
        if not force_refresh and self._access_token and now < self._token_expires_at - self._refresh_before:
            return self._access_token
        try:
            token, expires_in = self._fetch_token(force_refresh=force_refresh)
        except httpx.HTTPStatusError as e:
            raise WeChatMPClientError(f"获取 token 请求失败: {e}") from e
        except httpx.RequestError as e:
            raise WeChatMPClientError(f"获取 token 网络错误: {e}") from e
        self._access_token = token
        self._token_expires_at = now + expires_in
        logger.debug("WeChat MP access_token 已刷新（稳定版）")
        return self._access_token

    def _post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """带 token 的 POST，path 不含域名，如 /cgi-bin/draft/batchget"""
        token = self._ensure_token()
        url = f"{BASE_URL}{path}"
        params = {"access_token": token}
        payload = body or {}
        try:
            r = httpx.post(url, params=params, json=payload, timeout=30.0)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            raise WeChatMPClientError(f"请求失败: {e}") from e
        except httpx.RequestError as e:
            raise WeChatMPClientError(f"网络错误: {e}") from e
        errcode = data.get("errcode")
        if errcode and errcode != 0:
            if errcode == 40001 and not getattr(self, "_retrying_40001", False):
                self._access_token = None
                self._token_expires_at = 0
                self._retrying_40001 = True
                try:
                    return self._post(path, body)
                finally:
                    self._retrying_40001 = False
            raise WeChatMPClientError(
                f"接口错误: errcode={errcode}, errmsg={data.get('errmsg', '')}"
            )
        return data

    def _post_multipart(
        self,
        path: str,
        files: Dict[str, tuple],
        params_extra: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """带 token 的 multipart POST（用于上传文件）。用 requests 发请求，避免部分环境下 httpx 出现 SSL EOF。"""
        token = self._ensure_token()
        url = f"{BASE_URL}{path}"
        params = {"access_token": token, **(params_extra or {})}
        timeout = 60
        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                r = requests.post(
                    url, params=params, files=files, timeout=timeout
                )
                r.raise_for_status()
                data = r.json()
            except requests.exceptions.HTTPError as e:
                raise WeChatMPClientError(f"请求失败: {e}") from e
            except requests.exceptions.RequestError as e:
                last_err = e
                if attempt < 2:
                    time.sleep(1.0 + attempt * 0.5)
                    continue
                hint = " 若公众号开启了 API IP 白名单，请确认本机出口 IP 已加入白名单（mp.weixin.qq.com → 开发 → 基本配置）。"
                raise WeChatMPClientError(f"网络错误: {e}{hint}") from e
            errcode = data.get("errcode")
            if errcode and errcode != 0:
                if errcode == 40001 and not getattr(self, "_retrying_40001", False):
                    self._access_token = None
                    self._token_expires_at = 0
                    self._retrying_40001 = True
                    try:
                        return self._post_multipart(path, files, params_extra)
                    finally:
                        self._retrying_40001 = False
                raise WeChatMPClientError(
                    f"接口错误: errcode={errcode}, errmsg={data.get('errmsg', '')}"
                )
            return data
        hint = " 若公众号开启了 API IP 白名单，请确认本机出口 IP 已加入白名单（mp.weixin.qq.com → 开发 → 基本配置）。"
        raise WeChatMPClientError(f"网络错误: {last_err}{hint}") from last_err

    # ---------- 只读：草稿 ----------
    def get_draft_list(
        self,
        offset: int = 0,
        count: int = 20,
        no_content: int = 0,
    ) -> Dict[str, Any]:
        """获取草稿列表。no_content=1 不返回正文，减少体积。"""
        return self._post("/cgi-bin/draft/batchget", {
            "offset": offset,
            "count": min(20, max(1, count)),
            "no_content": 1 if no_content else 0,
        })

    def get_draft(self, media_id: str) -> Dict[str, Any]:
        """获取草稿详情（需从草稿列表拿到 media_id）。"""
        return self._post("/cgi-bin/draft/get", {"media_id": media_id})

    @staticmethod
    def _validate_content(content: str) -> None:
        """校验正文长度与体积，超限抛 WeChatMPClientError。"""
        if not content:
            return
        enc = content.encode("utf-8")
        if len(content) >= CONTENT_MAX_CHARS:
            raise WeChatMPClientError(
                f"正文不能超过 {CONTENT_MAX_CHARS} 字，当前 {len(content)} 字。请分段或使用「阅读原文」链接。"
            )
        if len(enc) >= CONTENT_MAX_BYTES:
            raise WeChatMPClientError(
                f"正文体积不能超过 1MB，当前约 {len(enc) // 1024}KB。请缩短内容或使用「阅读原文」。"
            )

    def _build_news_article(
        self,
        title: str,
        content: str,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        thumb_media_id: Optional[str] = None,
        content_source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构建单条图文消息（news）结构，供新增/更新草稿使用。"""
        self._validate_content(content)
        title = (title or "").strip()
        if not title:
            raise WeChatMPClientError("标题不能为空")
        # 不在此处限制标题长度，由微信公众号 API 校验；若超限 API 会报错，由调用方处理
        author = (author or "").strip()
        if author and len(author) > 16:
            author = author[:16]
        digest = (digest or "").strip()
        # 微信图文摘要（digest）限制 120 字，超限会报 45004 description size out of limit
        if digest and len(digest) > 120:
            digest = digest[:120]
        article = {
            "article_type": "news",
            "title": title,
            "content": content,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        if author:
            article["author"] = author
        if digest:
            article["digest"] = digest
        if thumb_media_id:
            article["thumb_media_id"] = thumb_media_id.strip()
        if content_source_url:
            url = (content_source_url or "").strip()
            if len(url.encode("utf-8")) > 1024:
                raise WeChatMPClientError("阅读原文链接过长（不超过 1KB）")
            article["content_source_url"] = url
        return article

    def add_draft(
        self,
        title: str,
        content: str,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        thumb_media_id: Optional[str] = None,
        content_source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """新增单篇图文草稿。thumb_media_id 为封面图素材 id（可选；若微信接口仍要求封面，调用会失败，可在草稿箱内补图后重试）。"""
        # 时间：2026-03-13；理由：写作助手同步到草稿箱允许先占位、后补封面；方法：不再在客户端前置拦截空 thumb。
        article = self._build_news_article(
            title=title,
            content=content,
            author=author,
            digest=digest,
            thumb_media_id=thumb_media_id,
            content_source_url=content_source_url,
        )
        return self._post("/cgi-bin/draft/add", {"articles": [article]})

    def update_draft(
        self,
        media_id: str,
        index: int,
        title: str,
        content: str,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        thumb_media_id: Optional[str] = None,
        content_source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """更新草稿中指定位置的图文。index 为第一篇 0。"""
        article = self._build_news_article(
            title=title,
            content=content,
            author=author,
            digest=digest,
            thumb_media_id=(thumb_media_id or "").strip() or None,
            content_source_url=content_source_url,
        )
        return self._post("/cgi-bin/draft/update", {
            "media_id": media_id.strip(),
            "index": index,
            "articles": article,
        })

    def upload_image_permanent(self, content: bytes, filename: str = "cover.jpg") -> Dict[str, Any]:
        """上传图片为永久素材，用于草稿封面。返回含 media_id、url。图片需 ≤2MB。仅支持 JPG/PNG（WebP 由上传接口层转为 PNG）。"""
        if len(content) > 2 * 1024 * 1024:
            raise WeChatMPClientError("封面图不能超过 2MB")
        ext = (filename or "").lower().split(".")[-1] if "." in (filename or "") else "jpg"
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png" if ext == "png" else "image/gif" if ext == "gif" else "image/bmp" if ext == "bmp" else "image/jpeg"
        files = {"media": (filename or "cover.jpg", content, mime)}
        return self._post_multipart("/cgi-bin/material/add_material", files, params_extra={"type": "image"})

    def upload_image_for_article(self, content: bytes, filename: str = "image.jpg") -> Dict[str, Any]:
        """上传图文消息内的图片，返回含 url。该 URL 用于正文 HTML 的 <img src="...">，不占素材库。图片需 ≤5MB。"""
        if len(content) > 5 * 1024 * 1024:
            raise WeChatMPClientError("正文图片不能超过 5MB")
        ext = (filename or "").lower().split(".")[-1] if "." in (filename or "") else "jpg"
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png" if ext == "png" else "image/gif" if ext == "gif" else "image/bmp" if ext == "bmp" else "image/jpeg"
        files = {"media": (filename or "image.jpg", content, mime)}
        return self._post_multipart("/cgi-bin/media/uploadimg", files)

    def batchget_material(
        self,
        material_type: str,
        offset: int = 0,
        count: int = 20,
    ) -> Dict[str, Any]:
        """获取永久素材列表。material_type: image/voice/video/news。返回含 total_count、item_count、item。"""
        count = min(20, max(1, count))
        return self._post("/cgi-bin/material/batchget_material", {
            "type": material_type,
            "offset": offset,
            "count": count,
        })

    def get_material(self, media_id: str) -> tuple[bytes, str]:
        """获取永久素材（如图片），返回 (二进制内容, content_type)。图片类返回二进制，错误时返回 JSON 并抛 WeChatMPClientError。"""
        token = self._ensure_token()
        url = f"{BASE_URL}/cgi-bin/material/get_material"
        params = {"access_token": token}
        payload = {"media_id": (media_id or "").strip()}
        if not payload["media_id"]:
            raise WeChatMPClientError("media_id 不能为空")
        try:
            r = httpx.post(url, params=params, json=payload, timeout=30.0)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise WeChatMPClientError(f"请求失败: {e}") from e
        except httpx.RequestError as e:
            raise WeChatMPClientError(f"网络错误: {e}") from e
        ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
        if ct in ("application/json", "text/plain", "text/html") or "json" in ct:
            data = r.json()
            errcode = data.get("errcode", 0)
            if errcode and errcode != 0:
                raise WeChatMPClientError(
                    f"获取素材失败: errcode={errcode}, errmsg={data.get('errmsg', '')}"
                )
            raise WeChatMPClientError("该素材不是图片类型，仅支持图片永久素材用于封面预览")
        if not r.content:
            raise WeChatMPClientError("获取素材返回为空")
        content_type = ct if ct and (ct.startswith("image/") or ct == "application/octet-stream") else "image/jpeg"
        return (r.content, content_type)
