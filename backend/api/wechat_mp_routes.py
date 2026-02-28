"""微信公众号只读与上传接口：草稿列表/详情、封面上传、正文图片上传（供任务与前端草稿箱使用）"""
from typing import Optional
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import Response
from backend.services.wechat_mp_service import WeChatMPClient, WeChatMPClientError
import logging

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
    """上传封面图为永久素材，返回 media_id，用于新增草稿时的 thumb_media_id。图片 ≤2MB。"""
    try:
        content = await file.read()
    except Exception as e:
        logger.exception("读取上传文件失败: %s", e)
        raise HTTPException(status_code=500, detail="读取文件失败")
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    filename = file.filename or "cover.jpg"
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
