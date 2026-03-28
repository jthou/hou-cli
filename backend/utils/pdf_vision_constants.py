"""PDF 页图识别：页分隔符与失败占位（与 docs/design/pdf-to-wiki-vision-extract-design.md §2.1 一致）"""


def pdf_vision_page_marker(page_1based: int) -> str:
    """第 page_1based 页起始标记（单独成行，不含正文）。"""
    return f"\n\n<!-- pdf-vision:page {int(page_1based)} -->\n\n"


def pdf_vision_page_fail_text(page_1based: int, reason: str = "") -> str:
    """单页 VL 失败时的正文占位（普通段落，不用 ## 标题）。"""
    r = (reason or "").strip().replace("\n", " ")
    if len(r) > 200:
        r = r[:197] + "…"
    if r:
        return f"（第 {int(page_1based)} 页：识别失败：{r}）\n\n"
    return f"（第 {int(page_1based)} 页：识别失败）\n\n"
