"""PDF 文本提取共享逻辑（时间：2025-03-15；理由：统一 pdf_routes、task_handlers、pdf_parser_tool 的提取实现）"""
from pathlib import Path
from typing import List


def get_pdf_layout_params():
    """分栏 PDF 布局参数：boxes_flow=None 按左下角排序，line_margin 放宽避免左右栏误合并"""
    from pdfminer.layout import LAParams
    return LAParams(boxes_flow=None, line_margin=0.8)


def _fix_doubled_pdf_text(text: str) -> str:
    """修复部分 PDF 渲染导致的重复字符（每字符出现两次）。相邻重复对占比 < 0.25 不处理。"""
    if not text or len(text) < 4:
        return text
    n = len(text)
    pairs = sum(1 for i in range(n - 1) if text[i] == text[i + 1])
    if n > 1 and pairs / (n - 1) < 0.25:
        return text
    undoubled = text[0::2]
    if len(undoubled) > 1:
        runs = sum(1 for i in range(len(undoubled) - 1) if undoubled[i] == undoubled[i + 1])
        if runs / (len(undoubled) - 1) >= 0.5:
            return text
    return undoubled


def extract_text_from_pdf(
    pdf_path: str | Path,
    page_numbers: List[int],
    use_layout: bool = True,
    fix_doubled: bool = False,
    columns: bool = False,
) -> str:
    """
    从 PDF 提取指定页的文本。
    :param pdf_path: PDF 文件路径
    :param page_numbers: 0-based 页码列表
    :param use_layout: 是否用 pdfminer 保持排版
    :param fix_doubled: 是否修复重复字符（部分 PDF 渲染问题）
    :param columns: 是否按分栏提取（boxes_flow=None, line_margin=0.8，改善多栏阅读顺序）
    """
    path_str = str(pdf_path)
    if not page_numbers:
        return ""

    # 优先 pdfminer
    if use_layout:
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract_text
            laparams = get_pdf_layout_params() if columns else None
            raw = pdfminer_extract_text(path_str, page_numbers=page_numbers, laparams=laparams)
            if raw and raw.strip():
                text = raw.strip()
                if fix_doubled:
                    text = _fix_doubled_pdf_text(text)
                return text
        except Exception:
            pass

    # 回退：pdfplumber
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return ""

    try:
        parts = []
        with pdfplumber.open(path_str) as pdf:
            for i in page_numbers:
                if 0 <= i < len(pdf.pages):
                    pg = pdf.pages[i]
                    try:
                        pg = pg.dedupe_chars(tolerance=3)
                    except Exception:
                        pass
                    t = pg.extract_text()
                    if t:
                        t = t.strip()
                        if fix_doubled:
                            t = _fix_doubled_pdf_text(t)
                        parts.append(t)
        return "\n\n".join(parts)
    except Exception:
        return ""
