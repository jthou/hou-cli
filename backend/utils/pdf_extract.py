"""PDF 文本提取共享逻辑（时间：2025-03-15；理由：统一 pdf_routes、task_handlers、pdf_parser_tool 的提取实现）"""
from pathlib import Path
from typing import List


def get_pdf_layout_params():
    """分栏 PDF 布局参数：boxes_flow=-1 优先按 x 排序，实现先左栏后右栏（避免按行交错）"""
    from pdfminer.layout import LAParams
    return LAParams(boxes_flow=-1.0, line_margin=0.8)


def _collect_textboxes(page) -> list:
    """递归收集页面中所有 LTTextBox，返回 [(x0, y0, text), ...]"""
    from pdfminer.layout import LTTextBox, LTContainer
    boxes = []
    for obj in page:
        if isinstance(obj, LTTextBox):
            t = obj.get_text().strip()
            if t:
                boxes.append((obj.x0, obj.y0, t))
        elif isinstance(obj, LTContainer):
            boxes.extend(_collect_textboxes(obj))
    return boxes


def _extract_page_columns_pdfplumber_words(path_str: str, page_idx: int, fix_doubled: bool) -> str:
    """用 pdfplumber extract_words 按行分栏：按行左边界 x0 判断列，先左栏后右栏（时间：2025-03-16；理由：pdfminer 按 (x0,-y0) 仍交错；方法：词→行→按列排序）"""
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(path_str) as pdf:
            if page_idx < 0 or page_idx >= len(pdf.pages):
                return ""
            pg = pdf.pages[page_idx]
            try:
                pg = pg.dedupe_chars(tolerance=3)
            except Exception:
                pass
            words = pg.extract_words() or []
            if not words:
                return ""
            w = pg.width
            col_threshold = w / 2
            line_tol = 3
            left_lines: list[tuple[float, list[tuple[float, str]]]] = []
            right_lines: list[tuple[float, list[tuple[float, str]]]] = []
            for wd in words:
                x0, top, text = wd.get("x0", 0), wd.get("top", 0), (wd.get("text") or "").strip()
                if not text:
                    continue
                is_left = x0 < col_threshold
                lines = left_lines if is_left else right_lines
                merged = False
                for i, (ltop, lwords) in enumerate(lines):
                    if abs(top - ltop) <= line_tol:
                        lwords.append((x0, text))
                        merged = True
                        break
                if not merged:
                    lines.append((top, [(x0, text)]))
            def line_text(lw: list[tuple[float, str]]) -> str:
                return " ".join(t for _, t in sorted(lw, key=lambda x: x[0]))
            left_col = [(t, line_text(lw)) for t, lw in left_lines]
            right_col = [(t, line_text(lw)) for t, lw in right_lines]
            left_col.sort(key=lambda x: x[0])
            right_col.sort(key=lambda x: x[0])
            parts = [x[1] for x in left_col] + [x[1] for x in right_col]
            text = "\n\n".join(parts)
            if fix_doubled:
                text = _fix_doubled_pdf_text(text)
            return text.strip()
    except Exception:
        return ""


def _extract_page_columns_pdfminer(path_str: str, page_idx: int, fix_doubled: bool) -> str:
    """用 pdfminer 提取文本框，按 (x0, -y0) 排序实现先左栏后右栏（时间：2025-03-16；理由：crop 会切断通栏段落；方法：取 bbox 按列排序）"""
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LAParams
        laparams = LAParams(line_margin=0.5)
        for i, page in enumerate(extract_pages(path_str, laparams=laparams)):
            if i == page_idx:
                boxes = _collect_textboxes(page)
                boxes.sort(key=lambda b: (b[0], -b[1]))
                text = "\n\n".join(b[2] for b in boxes)
                if fix_doubled:
                    text = _fix_doubled_pdf_text(text)
                return text.strip()
            if i > page_idx:
                break
    except Exception:
        pass
    return ""


def _extract_page_with_columns_pdfplumber(pdf, page_idx: int, fix_doubled: bool) -> str:
    """用 pdfplumber 裁剪左右半页分别提取（时间：2025-03-16；方法：crop 分栏；注意：会切断通栏段落）"""
    try:
        pg = pdf.pages[page_idx]
        try:
            pg = pg.dedupe_chars(tolerance=3)
        except Exception:
            pass
        w, h = pg.width, pg.height
        left = pg.crop((0, 0, 0.5 * w, h))
        right = pg.crop((0.5 * w, 0, w, h))
        l_text = left.extract_text() or ""
        r_text = right.extract_text() or ""
        if fix_doubled:
            l_text = _fix_doubled_pdf_text(l_text)
            r_text = _fix_doubled_pdf_text(r_text)
        return (l_text.strip() + "\n\n" + r_text.strip()).strip()
    except Exception:
        return ""


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
    :param columns: 是否按分栏提取（先左栏后右栏，避免交错）
    """
    path_str = str(pdf_path)
    if not page_numbers:
        return ""

    # columns=True 时优先用 pdfplumber extract_words 按行分栏（更稳），回退 pdfminer
    if columns:
        try:
            parts = []
            for i in page_numbers:
                t = _extract_page_columns_pdfplumber_words(path_str, i, fix_doubled)
                if not t:
                    t = _extract_page_columns_pdfminer(path_str, i, fix_doubled)
                if t:
                    parts.append(t)
            if parts:
                return "\n\n".join(parts)
        except Exception:
            pass

    # pdfminer
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

    # 回退：pdfplumber 默认（不分栏）
    try:
        import pdfplumber  # type: ignore
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
