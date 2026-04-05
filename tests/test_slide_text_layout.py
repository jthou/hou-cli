"""幻灯片正文方案：effective_text_scheme 与 Markdown 导出。"""

from backend.services.ppt_assistant.markdown import slide_deck_to_markdown
from backend.services.ppt_assistant.slide_text_layout import (
    effective_text_scheme,
    slide_body_long_text,
    TEXT_SCHEME_LONG_PROSE,
    TEXT_SCHEME_TITLE_LEAD,
    TEXT_SCHEME_TITLE_ONLY,
    TEXT_SCHEME_TITLE_SUBTITLE_LEAD,
)


def test_infer_title_lead():
    s = {"title": "A", "bullets": [], "lead": "短说明一句。"}
    assert effective_text_scheme(s) == TEXT_SCHEME_TITLE_LEAD


def test_infer_title_subtitle_lead():
    s = {"title": "A", "bullets": [], "subtitle": "小标题", "lead": "短段"}
    assert effective_text_scheme(s) == TEXT_SCHEME_TITLE_SUBTITLE_LEAD


def test_infer_long_prose():
    s = {"title": "A", "bullets": [], "body_text": "第一段。\n\n第二段。"}
    assert effective_text_scheme(s) == TEXT_SCHEME_LONG_PROSE


def test_explicit_scheme_title_only():
    s = {"title": "A", "text_scheme": "title_only", "bullets": []}
    assert effective_text_scheme(s) == TEXT_SCHEME_TITLE_ONLY


def test_slide_body_long_from_single_bullet():
    s = {
        "title": "A",
        "bullets": [{"text": "L1", "speaker_elaboration": "展开"}],
    }
    assert "L1" in slide_body_long_text(s)
    assert "展开" in slide_body_long_text(s)


def test_markdown_title_lead_not_bold_bullet():
    deck = {
        "deck_title": "D",
        "slides": [
            {
                "index": 1,
                "kind": "content",
                "title": "大标题",
                "bullets": [],
                "lead": "可见短说明，不要列表加粗",
            }
        ],
    }
    md = slide_deck_to_markdown(deck)
    assert "可见短说明" in md
    assert "- **可见短说明" not in md


def test_markdown_title_subtitle_lead():
    deck = {
        "deck_title": "D",
        "slides": [
            {
                "index": 1,
                "kind": "content",
                "title": "大标题",
                "bullets": [],
                "subtitle": "章节提要",
                "lead": "短段正文",
            }
        ],
    }
    md = slide_deck_to_markdown(deck)
    assert "### 章节提要" in md
    assert "短段正文" in md
