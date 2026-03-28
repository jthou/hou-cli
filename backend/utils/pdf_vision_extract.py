"""PDF 页图 → VL OCR（Markdown），与 web_reader OCR 提示词共用。"""
from __future__ import annotations

import base64
import logging
import os
from typing import Optional

from backend.utils.pdf_page_render import render_pdf_page_to_png
from backend.utils.pdf_vision_constants import pdf_vision_page_fail_text, pdf_vision_page_marker

logger = logging.getLogger(__name__)


def resolve_pdf_vision_model(explicit: Optional[str] = None) -> str:
    """PDF_VISION_MODEL → WEB_READER_OCR_MODEL → BROWSER_TOOL_VISION_MODEL → 默认。"""
    for v in (
        (explicit or "").strip(),
        (os.getenv("PDF_VISION_MODEL") or "").strip(),
        (os.getenv("WEB_READER_OCR_MODEL") or "").strip(),
        (os.getenv("BROWSER_TOOL_VISION_MODEL") or "").strip(),
    ):
        if v:
            return v
    return "qwen3-vl-plus-2025-12-19"


def pdf_vision_zoom_from_env() -> float:
    raw = (os.getenv("PDF_VISION_ZOOM") or "2").strip()
    try:
        z = float(raw)
        return z if z > 0 else 2.0
    except ValueError:
        return 2.0


async def ocr_single_page_png_to_markdown(
    png_bytes: bytes,
    *,
    page_1based: int,
    model: Optional[str] = None,
) -> str:
    """对单页 PNG 调用视觉模型，返回 Markdown 正文（可空）。"""
    if not png_bytes:
        raise ValueError("empty png")
    b64 = base64.b64encode(png_bytes).decode("ascii")
    image_url = f"data:image/png;base64,{b64}"
    from backend.api.web_reader_routes import OCR_PROMPT
    from backend.services.llm.llm_service import LLMService

    model_name = resolve_pdf_vision_model(model)
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
    return (text or "").strip()


async def extract_pdf_page_range_vision_markdown(
    pdf_path: str,
    page_from_1based: int,
    page_to_1based: int,
    *,
    zoom: Optional[float] = None,
    model: Optional[str] = None,
) -> str:
    """
    顺序处理 [page_from_1based, page_to_1based]（含）每一页：渲染 → VL → 拼接。
    不占满内存：每页 PNG 用后即弃。
    """
    z = float(zoom) if zoom is not None else pdf_vision_zoom_from_env()
    parts: list[str] = []
    for k in range(page_from_1based, page_to_1based + 1):
        parts.append(pdf_vision_page_marker(k))
        idx0 = k - 1
        try:
            png = render_pdf_page_to_png(pdf_path, idx0, zoom=z)
        except Exception as e:
            logger.warning("pdf vision render fail page=%s: %s", k, e)
            parts.append(pdf_vision_page_fail_text(k, str(e)))
            continue
        try:
            body = await ocr_single_page_png_to_markdown(
                png, page_1based=k, model=model
            )
        except Exception as e:
            logger.warning("pdf vision vl fail page=%s: %s", k, e)
            parts.append(pdf_vision_page_fail_text(k, str(e)))
            continue
        if body:
            parts.append(body + "\n\n")
    return "".join(parts).rstrip() + ("\n" if parts else "")
