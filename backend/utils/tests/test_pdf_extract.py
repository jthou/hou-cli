"""PDF 提取模块测试（时间：2025-03-16；理由：验证分栏提取逻辑）"""
import os
import tempfile
from pathlib import Path

import pytest

from backend.utils.pdf_extract import extract_text_from_pdf


def _create_two_column_pdf() -> Path:
    """创建两栏测试 PDF（左栏 x~72，右栏 x~350）"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        fd, p = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        c = canvas.Canvas(p, pagesize=letter)
        w, h = letter
        c.drawString(72, h - 72, "Left col line 1")
        c.drawString(72, h - 90, "Left col line 2")
        c.drawString(350, h - 72, "Right col line 1")
        c.drawString(350, h - 90, "Right col line 2")
        c.save()
        return Path(p)
    except ImportError:
        pytest.skip("reportlab not installed")


class TestExtractColumns:
    """分栏提取：先左栏后右栏，每栏内自上而下"""

    def test_columns_order_left_then_right(self):
        """左栏内容应在右栏前"""
        pdf = _create_two_column_pdf()
        try:
            r = extract_text_from_pdf(pdf, [0], columns=True)
            assert "Left col" in r and "Right col" in r
            assert r.find("Left col") < r.find("Right col")
        finally:
            pdf.unlink(missing_ok=True)

    def test_columns_order_within_left(self):
        """左栏内：line 1 在 line 2 前"""
        pdf = _create_two_column_pdf()
        try:
            r = extract_text_from_pdf(pdf, [0], columns=True)
            assert r.index("Left col line 1") < r.index("Left col line 2")
        finally:
            pdf.unlink(missing_ok=True)

    def test_columns_order_within_right(self):
        """右栏内：line 1 在 line 2 前"""
        pdf = _create_two_column_pdf()
        try:
            r = extract_text_from_pdf(pdf, [0], columns=True)
            assert r.index("Right col line 1") < r.index("Right col line 2")
        finally:
            pdf.unlink(missing_ok=True)

    def test_anthropic_skills_guide_page3_columns(self):
        """真实 PDF：Anthropic Skills 指南第 3 页，分栏应正确（左栏完整后再右栏）"""
        path = Path("/tmp/anthropic_skills_guide.pdf")
        if not path.exists():
            pytest.skip("运行前请下载: curl -o /tmp/anthropic_skills_guide.pdf https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf")
        # 第 3 页 Introduction（0-based=2）
        r = extract_text_from_pdf(path, [2], use_layout=True, columns=True)
        assert "Introduction" in r
        assert "A skill" in r or "A skil" in r  # PDF 字体可能丢 l
        assert "Two Paths Through This Guide" in r
        assert "Building standalone" in r
        # 关键：左栏 "how to handle" 应在右栏 "Two Paths Through" 之后、右栏 "Building standalone" 之前
        # 正确顺序：Introduction -> 左栏(含 how to handle) -> Two Paths -> 右栏(含 Building standalone)
        idx_how = r.find("how to handle")
        idx_two_paths = r.find("Two Paths Through")
        idx_building = r.find("Building standalone")
        assert idx_how >= 0 and idx_two_paths >= 0 and idx_building >= 0
        assert idx_how < idx_two_paths < idx_building, (
            f"分栏顺序错误: how at {idx_how}, Two Paths at {idx_two_paths}, Building at {idx_building}"
        )
