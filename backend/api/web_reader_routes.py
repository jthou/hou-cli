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

**矩阵与多行排版**：若出现矩阵、向量竖排或多行公式，请用 LaTeX 环境写出结构，不要用一行随意拼接：
- 方括号矩阵优先用 `bmatrix`（圆括号可用 `pmatrix`），独立成行时用双美元包裹整块，例如：
  $$\\begin{bmatrix} a_{11} & a_{12} \\\\ a_{21} & a_{22} \\end{bmatrix}$$
- 矩阵内**每一行**之间必须用 `\\\\` 换行；列与列之间用 `&` 分隔。
- 与原文一致的省略号请写成 `\\cdots`、`\\ldots` 等对应 LaTeX 命令，不要随意改成文字「…」混在公式里（若整段是公式环境内则保持命令形式）。

**表格**：若图片中有表格（含三线表、有线框表），请输出为 **Markdown 表格**（管道符 `|`），不要用纯空格对齐冒充表格：
- 第一行为表头，第二行为分隔行，仅含 `|---|` 这类短横线与竖线，列数与表头一致；自第三行起为数据行。
- 示例：
  | 列A | 列B |
  | --- | --- |
  | 单元格 | 单元格 |
- 单元格内换行可写成 `<br>` 或合并为一行用顿号分隔（择一保持全表一致）；空单元格用单个空格或 `-` 占位。
- 若存在跨行/跨列合并且难以用 Markdown 表达，在表前或表后用一行简短说明「某格合并」即可，其余仍按规整网格输出，不要省略整表。

只输出识别到的文字，不要添加任何解释或评论。"""

# 仅当请求带 source=weread 时追加：微信读书章节常为「4.1.4　标题」式编号，与通用网页 OCR 区分，避免误伤其它站点列表。
OCR_WEREAD_HEADING_SUPPLEMENT = """

**章节编号与 Markdown 标题（微信读书等电子书章节页）**：
若某行在版式上是**章节/小节标题**（通常字号更大或单独成行），且行首为**层级小节编号**（非正文句子里的数字），编号由若干**十进制整数**用英文句点 `.` 连接，例如 `4`、`4.1`、`4.1.4`，编号与标题文字之间常见全角空格 `　` 或半角空格，请将该行输出为 **Markdown ATX 标题**：
- `#` 的个数 = 编号中「`.` 分段」的个数：仅一段（如 `4`）用一级 `#`；两段（如 `4.1`）用 `##`；三段（如 `4.1.4`）用 `###`；依此类推，**最多六级** `######`。
- 输出形式示例：`### 4.1.4 数据滤波`、`## 4.1 某某节`（编号与标题正文均保留，与屏幕一致即可）。
- **不要**把明显的**有序列表**（如 `1.` 后接短词、多行并列列举）或正文中的「3.14」「2.3 节」这类**非标题行**改成标题；仅对视觉上明确是标题的行应用上述规则。
"""


class OcrRequest(BaseModel):
    """OCR 请求：base64 图片"""
    image: str  # data:image/png;base64,... 或纯 base64
    model: Optional[str] = None  # 可选，前端选择的视觉模型；未传则用 env 默认
    source: Optional[str] = None  # 如 weread：追加章节标题 Markdown 规则，仅微信读书页传入


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

        prompt = OCR_PROMPT
        if (req.source or "").strip().lower() == "weread":
            prompt = OCR_PROMPT + OCR_WEREAD_HEADING_SUPPLEMENT

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
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

        # 默认走百炼 qwen-max（需 BAILIAN_API_KEY）；勿再用 DEEPSEEK_MODEL，避免 DeepSeek 欠费时摘要失败
        model_name = (req.model or "").strip() or os.getenv("WEB_READER_SUMMARY_MODEL", "qwen-max")
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
    max_bytes = 40 * 1024 * 1024
    sub_to_ext = {
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "png": ".png",
        "gif": ".gif",
        "webp": ".webp",
    }
    for item in req.images:
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
