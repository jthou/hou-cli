"""幻灯片配图 prompt 构造（无网络）。"""

from backend.services.ppt_assistant.slide_image_service import build_slide_visual_prompt


def test_prompt_contains_title_and_bullets():
    deck = {"deck_title": "产品汇报"}
    slide = {
        "index": 2,
        "kind": "content",
        "title": "核心价值",
        "bullets": [{"text": "降本", "speaker_elaboration": "细说"}],
    }
    p = build_slide_visual_prompt(slide, deck, style_note="扁平风")
    assert "核心价值" in p
    assert "降本" in p
    assert "扁平风" in p
    assert "16:9" in p


def test_cover_prompt():
    deck = {"deck_title": "Q4"}
    slide = {"index": 1, "kind": "title", "title": "总结", "bullets": []}
    p = build_slide_visual_prompt(slide, deck)
    assert "总结" in p
    assert "Q4" in p
