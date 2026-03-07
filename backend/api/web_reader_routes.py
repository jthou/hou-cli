"""网页阅读 OCR 接口：截图 + Qwen-VL 提取文字"""
import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/web-reader", tags=["web-reader"])

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
