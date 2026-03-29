"""vision_ocr_prompts：与 web_reader / PDF VL 共用提示词组装。"""

from backend.utils.vision_ocr_prompts import OCR_WEREAD_HEADING_SUPPLEMENT, build_vision_ocr_prompt


def test_build_vision_ocr_prompt_default_has_math_and_table():
    p = build_vision_ocr_prompt()
    assert "数学公式" in p
    assert "Markdown 表格" in p
    assert "章节编号与 Markdown 标题" not in p


def test_build_vision_ocr_prompt_weread_appends_heading_supplement():
    p = build_vision_ocr_prompt(source="weread")
    assert "章节编号与 Markdown 标题" in p
    assert OCR_WEREAD_HEADING_SUPPLEMENT.strip()[:20] in p


def test_build_vision_ocr_prompt_weread_case_insensitive():
    assert build_vision_ocr_prompt(source="WeRead") == build_vision_ocr_prompt(source="weread")
