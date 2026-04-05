"""pptx_export：slide_deck → 字节流（依赖 python-pptx）。"""

import pytest

from backend.services.ppt_assistant.pptx_export import slide_deck_to_pptx_bytes

pytest.importorskip("pptx", reason="需要 python-pptx")


def test_export_rejects_empty_slides():
    with pytest.raises(ValueError, match="slides"):
        slide_deck_to_pptx_bytes({"deck_title": "X", "slides": []})


def test_export_minimal_deck_is_pptx_zip():
    deck = {
        "deck_title": "单元测试",
        "slides": [
            {"index": 1, "kind": "title", "title": "封面", "bullets": []},
            {
                "index": 2,
                "kind": "content",
                "title": "要点页",
                "bullets": [{"text": "A", "speaker_elaboration": "展开 A"}],
                "speaker_notes": "页级备注",
            },
        ],
    }
    raw = slide_deck_to_pptx_bytes(deck)
    assert raw[:2] == b"PK"
    assert len(raw) > 2000
