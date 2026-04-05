"""要点 slide_hint（片上短提示）与 bullet_to_dict。"""

from backend.services.ppt_assistant.bullets import (
    bullet_slide_hint,
    bullet_to_dict,
)
from backend.services.ppt_assistant.slide_image_service import build_slide_visual_prompt


def test_bullet_slide_hint_aliases():
    assert bullet_slide_hint({"text": "A", "slide_hint": "短"}) == "短"
    assert bullet_slide_hint({"text": "A", "hint": "x"}) == "x"
    assert bullet_slide_hint({"text": "A"}) == ""


def test_bullet_to_dict_includes_hint():
    d = bullet_to_dict(
        {"text": "标题", "slide_hint": "一句提示", "speaker_elaboration": "长文"}
    )
    assert d == {
        "text": "标题",
        "speaker_elaboration": "长文",
        "slide_hint": "一句提示",
    }


def test_bullet_to_dict_omits_empty_hint():
    d = bullet_to_dict({"text": "T", "speaker_elaboration": ""})
    assert "slide_hint" not in d


def test_visual_prompt_includes_hint():
    deck = {"deck_title": "D"}
    slide = {
        "index": 1,
        "kind": "content",
        "title": "页",
        "bullets": [
            {"text": "论点", "slide_hint": "短提示句", "speaker_elaboration": "很长" * 50}
        ],
    }
    p = build_slide_visual_prompt(slide, deck)
    assert "短提示句" in p
    assert "小字提示" in p or "短提示句" in p
