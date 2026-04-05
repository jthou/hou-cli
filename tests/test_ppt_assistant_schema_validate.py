"""ppt_assistant.schema_validate：纯逻辑单测。"""

from backend.services.ppt_assistant.bullets import bullet_parts
from backend.services.ppt_assistant.schema_validate import (
    coerce_ppt_elements,
    coerce_slide_deck,
    coerce_slide_object,
    validate_ppt_elements,
    validate_slide_deck,
    validate_slide_object,
)


def test_coerce_ppt_elements_fills_defaults():
    d = coerce_ppt_elements({"one_liner": "x"})
    assert d["version"] == 1
    assert isinstance(d["outline_sections"], list)
    assert isinstance(d["meta"], dict)


def test_validate_ppt_elements_minimal_ok():
    d = coerce_ppt_elements(
        {
            "version": 1,
            "one_liner": "a",
            "takeaway": "b",
            "outline_sections": [
                {
                    "id": "1",
                    "title": "T",
                    "summary": "",
                    "key_claims": [
                        {
                            "claim": "c",
                            "bullets": [],
                            "evidence_quotes": [],
                            "speaker_elaboration": "讲者",
                        }
                    ],
                }
            ],
            "highlight_numbers": [],
            "terms": [],
            "layout_hints": [],
        }
    )
    assert validate_ppt_elements(d) == []


def test_validate_slide_deck_single_final():
    d = coerce_slide_deck(
        {
            "version": 1,
            "deck_title": "D",
            "slides": [
                {
                    "index": 1,
                    "kind": "content",
                    "title": "t",
                    "bullets": ["x"],
                    "speaker_notes": "",
                }
            ],
        }
    )
    assert validate_slide_deck(d, single_slide_final=True) == []
    assert validate_slide_deck(d, single_slide_final=False) == []


def test_validate_slide_object_coerce_index_string():
    s = coerce_slide_object({"index": "2", "title": "x", "bullets": []})
    assert s["index"] == 2
    assert validate_slide_object(s) == []


def test_bullet_parts_after_coerce_slide():
    s = coerce_slide_object(
        {
            "index": 1,
            "kind": "content",
            "title": "t",
            "bullets": [{"text": "a", "speaker_elaboration": "e"}],
            "speaker_notes": "",
        }
    )
    t, e = bullet_parts(s["bullets"][0])
    assert t == "a" and e == "e"
