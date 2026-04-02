"""ppt_assistant.chunking 单测。"""

from backend.services.ppt_assistant.chunking import chunk_text


def test_chunk_single_when_short():
    assert chunk_text("hello", 100, 10) == ["hello"]


def test_chunk_overlap():
    t = "1234567890"
    parts = chunk_text(t, 4, 1)
    assert len(parts) >= 2
    joined = "".join(parts)
    assert len(joined) >= len(t)


def test_chunk_empty():
    assert chunk_text("", 100, 10) == []
    # 仅空白视为无有效内容，与 extract 空输入一致
    assert chunk_text("   ", 100, 10) == []
