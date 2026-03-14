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


class SummarizeRequest(BaseModel):
    """内容摘要请求"""
    content: str
    model: Optional[str] = None


class SummarizeResponse(BaseModel):
    success: bool
    summary: Optional[str] = None
    error: Optional[str] = None


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
