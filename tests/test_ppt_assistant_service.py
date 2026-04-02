"""ppt_assistant.service：mock LLM，不发起网络。"""

import pytest

from backend.services.ppt_assistant import slide_deck_to_markdown
from backend.services.ppt_assistant.bullets import bullet_parts
from backend.services.ppt_assistant.prompts import merge_user
from backend.services.ppt_assistant.service import (
    _normalize_meta,
    extract_ppt_elements,
    generate_slide_deck,
    run_ppt_pipeline,
)

MINIMAL_ELEMENTS_JSON = (
    '{"version":1,"meta":{"source_hint":"","audience":"","constraints_note":""},'
    '"one_liner":"L","takeaway":"T",'
    '"outline_sections":[{"id":"1","title":"A","summary":"s",'
    '"key_claims":[{"claim":"c","bullets":["b"],"evidence_quotes":[],"speaker_elaboration":"讲者参考示例"}]}],'
    '"highlight_numbers":[],"terms":[],"layout_hints":[]}'
)

def test_normalize_meta_includes_user_requirements():
    s = _normalize_meta(
        {"audience": "研发", "user_requirements": "突出安全性"}
    )
    assert "user_requirements:" in s
    assert "突出安全性" in s
    assert "audience:" in s


def test_merge_user_appends_context_note():
    u = merge_user('{"chunk":0}', "user_requirements: 只要三点")
    assert "【各片段抽取结果】" in u
    assert "【合并时请遵守" in u
    assert "只要三点" in u


MINIMAL_DECK_JSON = (
    '{"version":1,"deck_title":"D","slides":['
    '{"index":1,"kind":"content","title":"t","bullets":["x"],"speaker_notes":"n"}'
    "]}"
)


class FakeLLMExtractDeck:
    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        src = (audit_meta or {}).get("source", "")
        if src == "ppt_assistant_extract":
            return MINIMAL_ELEMENTS_JSON
        if src == "ppt_assistant_deck":
            return MINIMAL_DECK_JSON
        raise AssertionError(f"unexpected audit source: {src}")


@pytest.mark.asyncio
async def test_run_ppt_pipeline_mock():
    fake = FakeLLMExtractDeck()
    out = await run_ppt_pipeline("long article text here", llm=fake, chunk_chars=50_000)
    assert out["ppt_elements"]["one_liner"] == "L"
    assert out["slide_deck"]["deck_title"] == "D"
    md = slide_deck_to_markdown(out["slide_deck"])
    assert "D" in md


@pytest.mark.asyncio
async def test_run_elements_only():
    fake = FakeLLMExtractDeck()
    out = await run_ppt_pipeline(
        "x", llm=fake, chunk_chars=50_000, elements_only=True
    )
    assert out["ppt_elements"]["version"] == 1
    assert out["slide_deck"] is None


class FakeChunkMerge:
    partial_count = 0

    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        src = (audit_meta or {}).get("source", "")
        if src == "ppt_assistant_extract_partial":
            FakeChunkMerge.partial_count += 1
            return (
                '{"chunk_index":0,"outline_sections":[{"id":"s","title":"t","summary":"",'
                '"key_claims":[]}],"highlight_numbers":[],"terms":[]}'
            )
        if src == "ppt_assistant_merge":
            return (
                '{"version":1,"meta":{"source_hint":"","audience":"","constraints_note":""},'
                '"one_liner":"m","takeaway":"m","outline_sections":[],"highlight_numbers":[],'
                '"terms":[],"layout_hints":[]}'
            )
        raise AssertionError(f"unexpected {src}")


class FakeDeckMultiSlide:
    """模拟模型仍返回多页时，单页模式应合并为 1 张。"""

    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        return (
            '{"version":1,"deck_title":"合并标题","slides":['
            '{"index":1,"kind":"content","title":"a","bullets":["要点1"],"speaker_notes":""},'
            '{"index":2,"kind":"content","title":"b","bullets":["要点2"],"speaker_notes":"n2"}'
            "]}"
        )


@pytest.mark.asyncio
async def test_single_slide_merges_multiple_slides_from_llm():
    deck = await generate_slide_deck(
        {"version": 1, "one_liner": "x"},
        llm=FakeDeckMultiSlide(),
        single_slide=True,
    )
    assert len(deck["slides"]) == 1
    assert deck["slides"][0]["index"] == 1
    bs = deck["slides"][0]["bullets"]
    texts = [bullet_parts(b)[0] for b in bs]
    assert "要点1" in texts and "要点2" in texts


@pytest.mark.asyncio
async def test_multi_slide_keeps_multiple_slides():
    deck = await generate_slide_deck(
        {},
        llm=FakeDeckMultiSlide(),
        single_slide=False,
    )
    assert len(deck["slides"]) == 2


@pytest.mark.asyncio
async def test_extract_uses_chunking_when_long():
    FakeChunkMerge.partial_count = 0
    fake = FakeChunkMerge()
    text = "段落" * 80
    result = await extract_ppt_elements(text, llm=fake, chunk_chars=50, overlap=0)
    assert result["version"] == 1
    assert FakeChunkMerge.partial_count >= 2
