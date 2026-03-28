"""PDF 单页光栅化，供 pdf_to_wiki vision 路径使用（PyMuPDF）。"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def render_pdf_page_to_png(
    pdf_path: str | Path,
    page_index_0based: int,
    zoom: float = 2.0,
) -> bytes:
    """
    将 PDF 指定页渲染为 PNG 字节。
    :param pdf_path: 本地 PDF 路径
    :param page_index_0based: 0-based 页码
    :param zoom: 缩放（2.0 约等于提高清晰度，过大易触发 VL 像素上限）
    :raises FileNotFoundError: 文件不存在
    :raises ValueError: 非法页码或渲染失败
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ValueError("未安装 PyMuPDF（pymupdf），无法使用 PDF 页图识别") from e

    p = Path(pdf_path)
    if not p.is_file():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    z = float(zoom) if zoom else 2.0
    if z <= 0:
        z = 2.0

    doc = fitz.open(str(p))
    try:
        n = len(doc)
        if page_index_0based < 0 or page_index_0based >= n:
            raise ValueError(f"页码越界: {page_index_0based + 1}（共 {n} 页）")
        page = doc.load_page(page_index_0based)
        mat = fitz.Matrix(z, z)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out = pix.tobytes("png")
        if not out:
            raise ValueError(f"第 {page_index_0based + 1} 页渲染结果为空")
        return out
    finally:
        doc.close()
