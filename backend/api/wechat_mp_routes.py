"""微信公众号只读与上传接口：草稿列表/详情、封面上传、正文图片上传（供任务与前端草稿箱使用）"""
import io
import logging
import re
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import Response
from PIL import Image

from backend.services.wechat_mp_service import WeChatMPClient, WeChatMPClientError

router = APIRouter()
logger = logging.getLogger(__name__)

_client: Optional[WeChatMPClient] = None


def _get_client() -> WeChatMPClient:
    global _client
    if _client is None:
        try:
            _client = WeChatMPClient()
        except WeChatMPClientError as e:
            raise HTTPException(status_code=503, detail=str(e))
    return _client


def _parse_ip_from_response(r: requests.Response) -> Optional[str]:
    """从响应中解析 IP：先试 JSON 的 ip 字段，否则按纯文本取首行。"""
    try:
        data = r.json()
        if isinstance(data, dict):
            return data.get("ip") or None
    except Exception:
        pass
    raw = (r.text or "").strip()
    # 纯文本可能带换行，取第一行
    return raw.splitlines()[0].strip() if raw else None


def _fetch_outbound_ip() -> Optional[str]:
    """请求多个服务获取本机出口 IP，用 requests 避免部分环境下 httpx 的 SSL EOF。"""
    # 用户常用 ip.skk.moe 优先，其余作回退
    sources = [
        "https://ip.skk.moe/",
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
    ]
    for url in sources:
        try:
            r = requests.get(url, timeout=6)
            r.raise_for_status()
            ip = _parse_ip_from_response(r)
            if ip and re.match(r"^[\d.]+\Z", ip):
                return ip
        except Exception as e:
            logger.debug("出口 IP 源 %s 失败: %s", url, e)
            continue
    return None


@router.get("/wechat-mp/outbound-ip")
async def get_outbound_ip():
    """返回本机出口 IP，供公众号 API IP 白名单配置时复制使用。"""
    try:
        ip = _fetch_outbound_ip()
        if ip:
            return {"success": True, "ip": ip}
        return {"success": False, "ip": None, "detail": "无法获取出口 IP，请检查网络或代理"}
    except Exception as e:
        logger.warning("获取出口 IP 失败: %s", e)
        return {"success": False, "ip": None, "detail": "网络异常，请稍后重试"}


def _is_webp(content_type: Optional[str], filename: str) -> bool:
    """判断是否为 WebP：按 Content-Type 或扩展名。"""
    if content_type and "webp" in content_type.lower():
        return True
    fn = (filename or "").lower()
    return fn.endswith(".webp")


def _webp_to_png(content: bytes) -> bytes:
    """将 WebP 图片转为 PNG 字节流，供公众号封面上传（公众号封面仅支持 JPG/PNG）。"""
    try:
        img = Image.open(io.BytesIO(content))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()
    except Exception as e:
        logger.warning("WebP 转 PNG 失败: %s", e)
        raise HTTPException(status_code=400, detail=f"WebP 转 PNG 失败: {e}") from e


@router.get("/wechat-mp/materials/images")
async def list_image_materials(offset: int = 0, count: int = 20):
    """获取公众号永久图片素材列表，供封面等选择。返回 media_id、name、update_time。"""
    try:
        client = _get_client()
        data = client.batchget_material("image", offset=offset, count=min(20, max(1, count)))
        item = data.get("item")
        if not isinstance(item, list):
            item = []
        return {
            "success": True,
            "total_count": data.get("total_count", 0),
            "item_count": data.get("item_count", 0),
            "item": item,
        }
    except WeChatMPClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/wechat-mp/drafts")
async def list_drafts(offset: int = 0, count: int = 20, no_content: int = 1):
    """获取公众号草稿列表。no_content=1 不返回正文以减小体积。"""
    try:
        client = _get_client()
        data = client.get_draft_list(offset=offset, count=min(20, max(1, count)), no_content=no_content)
        # 保证前端拿到的 item 始终为数组（微信有时不返回 item 键）
        item = data.get("item")
        if not isinstance(item, list):
            item = []
        return {"success": True, "total_count": data.get("total_count", 0), "item_count": data.get("item_count", 0), "item": item}
    except WeChatMPClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/wechat-mp/cover-image")
async def get_cover_image(media_id: str):
    """根据封面素材 media_id 拉取图片并返回，供前端预览展示。"""
    if not (media_id or "").strip():
        raise HTTPException(status_code=400, detail="media_id 不能为空")
    try:
        client = _get_client()
        content, content_type = client.get_material(media_id.strip())
        return Response(content=content, media_type=content_type or "image/jpeg")
    except WeChatMPClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/wechat-mp/drafts/detail")
async def get_draft_detail(media_id: str):
    """获取单篇草稿详情（用于展示或编辑预填）。"""
    if not (media_id or "").strip():
        raise HTTPException(status_code=400, detail="media_id 不能为空")
    try:
        client = _get_client()
        data = client.get_draft(media_id.strip())
        return {"success": True, "draft": data}
    except WeChatMPClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wechat-mp/upload-cover")
async def upload_cover(file: UploadFile = File(...)):
    """上传封面图为永久素材，返回 media_id。支持 JPG/PNG；WebP 会自动转为 PNG。图片 ≤2MB。"""
    try:
        content = await file.read()
    except Exception as e:
        logger.exception("读取上传文件失败: %s", e)
        raise HTTPException(status_code=500, detail="读取文件失败")
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    filename = file.filename or "cover.jpg"
    content_type = getattr(file, "content_type", None) or ""
    if _is_webp(content_type, filename):
        content = _webp_to_png(content)
        filename = "cover.png"
    try:
        client = _get_client()
        data = client.upload_image_permanent(content, filename=filename)
        return {"success": True, "media_id": data.get("media_id"), "url": data.get("url")}
    except WeChatMPClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wechat-mp/upload-article-image")
async def upload_article_image(file: UploadFile = File(...)):
    """上传图文消息内的图片，返回 url，用于正文 HTML 中的 <img src="...">。图片 ≤5MB。"""
    try:
        content = await file.read()
    except Exception as e:
        logger.exception("读取上传文件失败: %s", e)
        raise HTTPException(status_code=500, detail="读取文件失败")
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    filename = file.filename or "image.jpg"
    try:
        client = _get_client()
        data = client.upload_image_for_article(content, filename=filename)
        url = data.get("url")
        if not url:
            raise HTTPException(status_code=502, detail="微信未返回图片 URL")
        return {"success": True, "url": url}
    except WeChatMPClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
