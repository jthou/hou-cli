"""图像服务：参考图 URL 归一化（无网络）。"""

from backend.services.llm.image_gen_service import (
    _model_supports_reference_images,
    _normalize_reference_image_urls,
)
from backend.services.ppt_assistant.slide_image_service import (
    valid_slide_indexes_from_deck,
)


def test_normalize_reference_urls_dedup_and_cap():
    raw = [
        "https://a/x.png",
        "https://a/x.png",
        "ftp://bad",
        "https://b/y.png",
        "https://c/z.png",
        "https://d/w.png",
    ]
    out = _normalize_reference_image_urls(raw, max_n=3)
    assert out == ["https://a/x.png", "https://b/y.png", "https://c/z.png"]


def test_normalize_accepts_data_uri():
    s = "data:image/png;base64,abcd"
    assert _normalize_reference_image_urls([s]) == [s]


def test_model_supports_refs_wan_image():
    assert _model_supports_reference_images("wan2.6-image") is True


def test_model_supports_refs_t2i_false():
    assert _model_supports_reference_images("wan2.6-t2i") is False


def test_valid_slide_indexes_from_deck():
    deck = {
        "slides": [
            {"index": 3, "kind": "title", "title": "A", "bullets": []},
            {"index": 1, "kind": "content", "title": "B", "bullets": []},
        ]
    }
    assert valid_slide_indexes_from_deck(deck) == {1, 3}
