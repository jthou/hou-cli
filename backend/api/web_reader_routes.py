"""网页阅读 OCR 接口：截图 + Qwen-VL 提取文字；正文配图经扩展拉取后落盘供 Markdown 引用"""
import base64
import logging
import os
import re
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from shared.platform_utils import get_app_data_dir

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/web-reader", tags=["web-reader"])

# 时间：2026-03-14；理由：微信等站配图防盗链，扩展拉取后落盘；方法：UUID 文件名 + 仅匹配安全路径
_INLINE_IMG_DIR: Path = get_app_data_dir() / "web_reader_inline_images"
_INLINE_IMG_DIR.mkdir(parents=True, exist_ok=True)
_DATA_URL_INLINE_RE = re.compile(
    r"^data:image/(jpeg|jpg|png|gif|webp);base64,([\s\S]+)$",
    re.IGNORECASE,
)
_SAFE_INLINE_NAME = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(jpg|jpeg|png|gif|webp)$",
    re.IGNORECASE,
)

OCR_PROMPT = """请识别图片中的所有文字，按原文顺序逐行输出。如果是书籍或文章页面，请完整提取正文内容，保留段落结构。

**数学公式**：若图片中有数学公式（如 LaTeX、算式、符号等），请用以下格式包裹：
- 行内公式：用单个美元符号包裹，如 $E=mc^2$
- 独立成行的公式：用双美元符号包裹，如 $$\\int_0^1 x\\,dx = \\frac{1}{2}$$

只输出识别到的文字，不要添加任何解释或评论。"""


class OcrRequest(BaseModel):
    """OCR 请求：base64 图片"""
    image: str  # data:image/png;base64,... 或纯 base64
    model: Optional[str] = None  # 可选，前端选择的视觉模型；未传则用 env 默认


class OcrResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None


class SummarizeRequest(BaseModel):
    """内容摘要请求"""
    content: str
    model: Optional[str] = None


class SummarizeResponse(BaseModel):
    success: bool
    summary: Optional[str] = None
    error: Optional[str] = None


class InlineImageItem(BaseModel):
    """扩展拉取后的单张图：原始 URL + data URL"""

    original_url: str
    data_url: str


class MaterializeInlineImagesRequest(BaseModel):
    images: List[InlineImageItem]


SUMMARY_PROMPT = """请对以下文本生成**结构化、分层摘要**，尽可能覆盖原文所有重要内容。

**输出格式要求**（使用 Markdown）：
1. 按主题/章节分层，使用 ## 一级标题、### 二级标题
2. 每层下用 - 或 1. 2. 3. 列出要点
3. 三级结构：一级主题 → 二级要点 → 三级细节（如有）
4. 尽量覆盖原文所有段落、论点、数据、结论，不遗漏重要信息
5. 保留关键术语、数字、人名、时间等
6. 只输出摘要内容，不要添加「本文介绍了」等前言或总结语

**示例结构**：
## 一、主题A
- 要点1
  - 细节或子要点
- 要点2
## 二、主题B
### 2.1 子主题
- 内容...
### 2.2 子主题
- 内容...
## 三、...
"""


def _get_vision_model() -> str:
    """获取视觉模型，优先环境变量（与 vision_providers 默认一致）"""
    return os.getenv(
        "WEB_READER_OCR_MODEL",
        os.getenv("BROWSER_TOOL_VISION_MODEL", "qwen3-vl-plus-2025-12-19"),
    )


@router.post("/ocr", response_model=OcrResponse)
async def ocr_image(req: OcrRequest):
    """
    对截图进行 OCR，使用 Qwen-VL 等视觉模型提取文字。
    用于微信读书等 Canvas 渲染页面，无法从 DOM 提取时。
    """
    raw = (req.image or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="缺少 image 参数")

    # 解析为 data URL
    if raw.startswith("data:") and ";base64," in raw:
        image_url = raw
    elif raw:
        image_url = f"data:image/png;base64,{raw}"
    else:
        raise HTTPException(status_code=400, detail="无效的 image 格式")

    try:
        from backend.services.llm.llm_service import LLMService

        model_name = (req.model or "").strip() or _get_vision_model()
        llm = LLMService(model=model_name)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]

        text = await llm.chat(messages=messages)
        return OcrResponse(success=True, text=(text or "").strip())

    except Exception as e:
        logger.exception("OCR 失败")
        return OcrResponse(success=False, error=str(e))


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_content(req: SummarizeRequest):
    """
    对正文内容生成 LLM 摘要，供 MarkdownEditorPreview 等使用。
    """
    content = (req.content or "").strip()
    if not content:
        return SummarizeResponse(success=False, error="内容为空")

    try:
        from backend.services.llm.llm_service import LLMService

        model_name = (req.model or "").strip() or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        llm = LLMService(model=model_name)

        messages = [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": content[:50000]},  # 限制长度
        ]

        summary = await llm.chat(messages=messages)
        return SummarizeResponse(success=True, summary=(summary or "").strip())

    except Exception as e:
        logger.exception("摘要生成失败")
        return SummarizeResponse(success=False, error=str(e))


@router.post("/materialize-inline-images")
async def materialize_inline_images(req: MaterializeInlineImagesRequest):
    """
    将扩展传来的 data URL 图片写入本地，返回 original_url -> /api/web-reader/inline-static/{uuid}.ext
    供 Markdown 使用本站可访问地址（避免微信 CDN 跨域/防盗链）。
    """
    mapping: dict = {}
    max_bytes = 6 * 1024 * 1024
    max_items = 50
    sub_to_ext = {
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "png": ".png",
        "gif": ".gif",
        "webp": ".webp",
    }
    for item in req.images[:max_items]:
        ou = (item.original_url or "").strip()
        if not ou.startswith(("http://", "https://")):
            continue
        raw_du = (item.data_url or "").strip().replace("\n", "").replace("\r", "")
        m = _DATA_URL_INLINE_RE.match(raw_du)
        if not m:
            continue
        sub = m.group(1).lower()
        b64 = m.group(2).strip()
        ext = sub_to_ext.get(sub)
        if not ext:
            continue
        try:
            raw = base64.b64decode(b64, validate=True)
        except Exception:
            continue
        if not raw or len(raw) > max_bytes:
            continue
        fid = str(uuid.uuid4())
        fname = f"{fid}{ext}"
        path = _INLINE_IMG_DIR / fname
        try:
            path.write_bytes(raw)
        except OSError as e:
            logger.warning("inline image write failed: %s", e)
            continue
        mapping[ou] = f"/api/web-reader/inline-static/{fname}"

    return {"success": True, "mapping": mapping}


@router.get("/inline-static/{filename}")
async def serve_inline_image(filename: str):
    if not _SAFE_INLINE_NAME.match(filename):
        raise HTTPException(status_code=404, detail="Not found")
    path = _INLINE_IMG_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)
