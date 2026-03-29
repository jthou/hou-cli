"""PDF 页图 → VL OCR（Markdown）；提示词经 backend.utils.vision_ocr_prompts 与 web_reader 统一。"""
from __future__ import annotations

import base64
import logging
import os
from typing import Any, List, Optional

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
    ocr_source: Optional[str] = None,
) -> str:
    """ocr_source=weread 时与 web_reader /ocr 一致，追加章节标题 Markdown 规则。"""
    if not png_bytes:
        raise ValueError("empty png")
    b64 = base64.b64encode(png_bytes).decode("ascii")
    image_url = f"data:image/png;base64,{b64}"
    from backend.services.llm.llm_service import LLMService
    from backend.utils.vision_ocr_prompts import build_vision_ocr_prompt

    model_name = resolve_pdf_vision_model(model)
    llm = LLMService(model=model_name)
    prompt = build_vision_ocr_prompt(source=ocr_source)
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
    return (text or "").strip()


async def extract_pdf_vision_pages_detail(
    pdf_path: str,
    page_indices_0based: List[int],
    *,
    zoom: Optional[float] = None,
    model: Optional[str] = None,
    ocr_source: Optional[str] = None,
) -> List[dict[str, Any]]:
    """逐页渲染 → VL，返回 [{\"page\": 1-based, \"text\": markdown}, …]（供阅读页与 Wiki 拼接）。"""
    z = float(zoom) if zoom is not None else pdf_vision_zoom_from_env()
    out: list[dict[str, Any]] = []
    for idx0 in page_indices_0based:
        k = idx0 + 1
        try:
            png = render_pdf_page_to_png(pdf_path, idx0, zoom=z)
        except Exception as e:
            logger.warning("pdf vision render fail page=%s: %s", k, e)
            out.append({"page": k, "text": pdf_vision_page_fail_text(k, str(e)).strip()})
            continue
        try:
            body = await ocr_single_page_png_to_markdown(
                png, page_1based=k, model=model, ocr_source=ocr_source
            )
        except Exception as e:
            logger.warning("pdf vision vl fail page=%s: %s", k, e)
            out.append({"page": k, "text": pdf_vision_page_fail_text(k, str(e)).strip()})
            continue
        out.append({"page": k, "text": (body or "").strip()})
    return out


async def extract_pdf_page_range_vision_markdown(
    pdf_path: str,
    page_from_1based: int,
    page_to_1based: int,
    *,
    zoom: Optional[float] = None,
    model: Optional[str] = None,
    ocr_source: Optional[str] = None,
) -> str:
    """顺序逐页：渲染 → VL → 拼接（含 wiki 用页标记）；每页 PNG 不攒全 chunk。"""
    if page_to_1based < page_from_1based:
        page_from_1based, page_to_1based = page_to_1based, page_from_1based
    indices = list(range(page_from_1based - 1, page_to_1based))
    rows = await extract_pdf_vision_pages_detail(
        pdf_path, indices, zoom=zoom, model=model, ocr_source=ocr_source
    )
    parts: list[str] = []
    for row in rows:
        parts.append(pdf_vision_page_marker(int(row["page"])))
        body = (row.get("text") or "").strip()
        if body:
            parts.append(body + "\n\n")
    return "".join(parts).rstrip() + ("\n" if parts else "")
