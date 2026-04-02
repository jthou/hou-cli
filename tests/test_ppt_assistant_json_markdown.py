"""json_extract 与 markdown 转换。"""

import pytest

from backend.services.ppt_assistant.json_extract import parse_llm_json_object
from backend.services.ppt_assistant.markdown import slide_deck_to_markdown


def test_parse_json_raw():
    assert parse_llm_json_object('{"a":1}') == {"a": 1}


def test_parse_json_fenced():
    text = 'Here:\n```json\n{"x": true}\n```\n'
    assert parse_llm_json_object(text) == {"x": True}


def test_parse_json_extra_text():
    assert parse_llm_json_object('prefix {"b": 2} suffix') == {"b": 2}


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse_llm_json_object("no json")


def test_slide_deck_markdown():
    deck = {
        "version": 1,
        "deck_title": "Demo",
        "slides": [
            {
                "index": 1,
                "kind": "title",
                "title": "封面",
                "bullets": [],
                "speaker_notes": "开场",
            },
            {
                "index": 2,
                "kind": "content",
                "title": "要点",
                "bullets": ["a", "b"],
                "speaker_notes": "",
            },
        ],
    }
    md = slide_deck_to_markdown(deck)
    assert "# Demo" in md
    assert "第 1 页" in md
    assert "第 2 页" in md
    assert "- **a**" in md


def test_slide_deck_markdown_elaboration():
    deck = {
        "version": 1,
        "deck_title": "X",
        "slides": [
            {
                "index": 1,
                "kind": "content",
                "title": "t",
                "bullets": [
                    {"text": "短句", "speaker_elaboration": "这里展开约两百字讲者参考稿。"},
                ],
                "speaker_notes": "",
            }
        ],
    }
    md = slide_deck_to_markdown(deck)
    assert "- **短句**" in md
    assert "两百字" in md
    assert "  > " in md
