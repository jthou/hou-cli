"""PDF 页图路径：常量与渲染（无 VL 调用）"""

import pytest

from backend.utils.pdf_vision_constants import pdf_vision_page_fail_text, pdf_vision_page_marker


def test_pdf_vision_page_marker_format():
    assert "pdf-vision:page 1" in pdf_vision_page_marker(1)


def test_pdf_vision_page_fail_text():
    assert "第 2 页" in pdf_vision_page_fail_text(2)
    assert "识别失败" in pdf_vision_page_fail_text(2, "timeout")
    assert "…" in pdf_vision_page_fail_text(2, "x" * 300)


def test_render_pdf_page_to_png_minimal(tmp_path):
    try:
        import fitz
    except ImportError:
        pytest.skip("pymupdf 未安装")
    pdf_path = tmp_path / "one.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "hi")
    doc.save(str(pdf_path))
    doc.close()

    from backend.utils.pdf_page_render import render_pdf_page_to_png

    png = render_pdf_page_to_png(pdf_path, 0, zoom=1.5)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"

    with pytest.raises(ValueError):
        render_pdf_page_to_png(pdf_path, 99, zoom=1.5)


def test_render_pdf_page_to_png_missing_file(tmp_path):
    from backend.utils.pdf_page_render import render_pdf_page_to_png

    p = tmp_path / "missing.pdf"
    with pytest.raises(FileNotFoundError):
        render_pdf_page_to_png(p, 0)
