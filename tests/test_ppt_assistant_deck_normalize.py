from backend.services.ppt_assistant.deck_normalize import enforce_single_slide_deck


def test_enforce_merges_slides():
    deck = {
        "version": 1,
        "deck_title": "总题",
        "slides": [
            {"index": 1, "kind": "content", "title": "A", "bullets": ["x"], "speaker_notes": ""},
            {"index": 2, "kind": "transition", "title": "过场", "bullets": [], "speaker_notes": ""},
            {"index": 3, "kind": "content", "title": "B", "bullets": ["x", "y"], "speaker_notes": "n"},
        ],
    }
    out = enforce_single_slide_deck(deck)
    assert len(out["slides"]) == 1
    assert out["slides"][0]["title"] == "总题"
    assert out["slides"][0]["bullets"] == [
        {"text": "x", "speaker_elaboration": ""},
        {"text": "y", "speaker_elaboration": ""},
    ]


def test_enforce_one_slide_unchanged():
    deck = {
        "deck_title": "D",
        "slides": [{"index": 3, "kind": "content", "title": "t", "bullets": ["a"], "speaker_notes": ""}],
    }
    out = enforce_single_slide_deck(deck)
    assert len(out["slides"]) == 1
    assert out["slides"][0]["index"] == 1
    assert out["slides"][0]["bullets"] == [{"text": "a", "speaker_elaboration": ""}]
