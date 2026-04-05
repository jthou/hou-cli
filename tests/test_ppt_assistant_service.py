"""ppt_assistant.service：mock LLM，不发起网络。"""

import pytest

from backend.services.ppt_assistant import slide_deck_to_markdown
from backend.services.ppt_assistant.bullets import bullet_parts
from backend.services.ppt_assistant.prompts import merge_user
from backend.services.ppt_assistant.service import (
    _normalize_meta,
    extract_ppt_elements,
    generate_slide_deck,
    refine_slide_deck,
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


class FakeParallelPlanDeck:
    """模拟并行模式：先返回 deck_plan，再为每页返回 slide JSON。"""

    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        src = (audit_meta or {}).get("source", "")
        if src == "ppt_assistant_deck_plan":
            return (
                '{"version":1,"deck_title":"并行标题","slides":['
                '{"index":1,"kind":"content","title":"页1","bullets":["A","B"]},'
                '{"index":2,"kind":"content","title":"页2","bullets":["C"]}'
                "]}"
            )
        if src.startswith("ppt_assistant_deck_page_"):
            idx = int(src.split("_")[-1])
            if idx == 1:
                return (
                    '{"index":1,"kind":"content","title":"页1",'
                    '"bullets":['
                    '{"text":"A","speaker_elaboration":"讲者A"},'
                    '{"text":"B","speaker_elaboration":"讲者B"}'
                    '],'
                    '"speaker_notes":"note1"}'
                )
            if idx == 2:
                return (
                    '{"index":2,"kind":"content","title":"页2",'
                    '"bullets":[{"text":"C","speaker_elaboration":"讲者C"}],'
                    '"speaker_notes":"note2"}'
                )
            raise AssertionError("unexpected page idx")
        raise AssertionError(f"unexpected audit source: {src}")


@pytest.mark.asyncio
async def test_generate_slide_deck_parallel_produces_multiple_pages():
    deck = await generate_slide_deck(
        {"version": 1, "one_liner": "x"},
        llm=FakeParallelPlanDeck(),
        single_slide=False,
        generation_mode="parallel",
        parallelism=2,
        max_repair_attempts=0,
    )
    assert deck["deck_title"] == "并行标题"
    assert len(deck["slides"]) == 2
    texts_page1 = [bullet_parts(b)[0] for b in deck["slides"][0]["bullets"]]
    texts_page2 = [bullet_parts(b)[0] for b in deck["slides"][1]["bullets"]]
    assert "A" in texts_page1 and "B" in texts_page1
    assert texts_page2 == ["C"]


class FakeParallelPlanDeckFailOne(FakeParallelPlanDeck):
    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        src = (audit_meta or {}).get("source", "")
        if src == "ppt_assistant_deck_plan":
            return (
                '{"version":1,"deck_title":"并行标题","slides":['
                '{"index":1,"kind":"content","title":"页1","bullets":["A","B"]},'
                '{"index":2,"kind":"content","title":"页2","bullets":["C"]}'
                "]}"
            )
        if src.startswith("ppt_assistant_deck_page_"):
            idx = int(src.split("_")[-1])
            if idx == 1:
                return (
                    '{"index":1,"kind":"content","title":"页1",'
                    '"bullets":['
                    '{"text":"A","speaker_elaboration":"讲者A"},'
                    '{"text":"B","speaker_elaboration":"讲者B"}'
                    '],'
                    '"speaker_notes":"note1"}'
                )
            if idx == 2:
                raise RuntimeError("mock failure on page 2")
        raise AssertionError(f"unexpected audit source: {src}")


@pytest.mark.asyncio
async def test_generate_slide_deck_parallel_emits_slide_failed_and_placeholders():
    failures: list[tuple[int, str]] = []

    def on_failed(page_index: int, error: str):
        failures.append((page_index, error))

    deck = await generate_slide_deck(
        {"version": 1, "one_liner": "x"},
        llm=FakeParallelPlanDeckFailOne(),
        single_slide=False,
        generation_mode="parallel",
        parallelism=2,
        max_repair_attempts=0,
        on_slide_failed=on_failed,
    )
    assert len(deck["slides"]) == 2
    assert deck["slides"][1]["title"] == "生成失败（占位）"
    assert failures and failures[0][0] == 2


class FakeParallelPlanDeckWithSources:
    """并行 Draft + page_inputs sources 强对齐：输出每页 sources。"""

    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        src = (audit_meta or {}).get("source", "")
        if src == "ppt_assistant_deck_plan":
            return (
                '{"version":1,"deck_title":"并行标题","slides":['
                '{"index":1,"kind":"content","title":"页1","bullets":["WRONG1"]},'
                '{"index":2,"kind":"content","title":"页2","bullets":["WRONG2"]}'
                "]}"
            )
        if src.startswith("ppt_assistant_deck_page_"):
            idx = int(src.split("_")[-1])
            if idx == 1:
                return (
                    '{"index":1,"kind":"content","title":"页1",'
                    '"bullets":[{"text":"A","speaker_elaboration":"讲者A"}],'
                    '"speaker_notes":"note1",'
                    '"sources":["src1"]}'
                )
            if idx == 2:
                return (
                    '{"index":2,"kind":"content","title":"页2",'
                    '"bullets":[{"text":"C","speaker_elaboration":"讲者C"}],'
                    '"speaker_notes":"note2",'
                    '"sources":["src2"]}'
                )
        raise AssertionError(f"unexpected audit source: {src}")


@pytest.mark.asyncio
async def test_generate_slide_deck_parallel_page_inputs_sources_match():
    deck = await generate_slide_deck(
        {"version": 1, "one_liner": "x"},
        llm=FakeParallelPlanDeckWithSources(),
        single_slide=False,
        generation_mode="parallel",
        parallelism=2,
        max_repair_attempts=0,
        page_inputs=[
            {"index": 1, "title_hint": "页1", "bullets_hint": ["A"], "sources": ["src1"]},
            {"index": 2, "title_hint": "页2", "bullets_hint": ["C"], "sources": ["src2"]},
        ],
    )
    assert deck["slides"][0]["sources"] == ["src1"]
    assert deck["slides"][1]["sources"] == ["src2"]


@pytest.mark.asyncio
async def test_extract_uses_chunking_when_long():
    FakeChunkMerge.partial_count = 0
    fake = FakeChunkMerge()
    text = "段落" * 80
    result = await extract_ppt_elements(text, llm=fake, chunk_chars=50, overlap=0)
    assert result["version"] == 1
    assert FakeChunkMerge.partial_count >= 2


class FakeRefineLLM:
    """refine：返回新标题与新要点；repair 同源。"""

    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        src = (audit_meta or {}).get("source", "")
        if src in ("ppt_assistant_refine_slide", "ppt_assistant_refine_slide_repair"):
            return (
                '{"index":1,"kind":"content","title":"新标题","bullets":["新要点"],'
                '"speaker_notes":"sn"}'
            )
        raise AssertionError(f"unexpected audit source: {src}")


@pytest.mark.asyncio
async def test_refine_slide_deck_updates_unlocked_fields():
    deck = {
        "version": 1,
        "deck_title": "D",
        "slides": [
            {
                "index": 1,
                "kind": "content",
                "title": "旧标题",
                "bullets": ["旧要点"],
                "speaker_notes": "",
            }
        ],
    }
    out = await refine_slide_deck(
        deck,
        target_slide_indexes=[1],
        instructions="改得更正式",
        llm=FakeRefineLLM(),
        max_repair_attempts=2,
    )
    assert out["slides"][0]["title"] == "新标题"
    texts = [bullet_parts(b)[0] for b in out["slides"][0]["bullets"]]
    assert "新要点" in texts


@pytest.mark.asyncio
async def test_refine_slide_deck_locks_title():
    deck = {
        "version": 1,
        "deck_title": "D",
        "slides": [
            {
                "index": 1,
                "kind": "content",
                "title": "旧标题",
                "bullets": ["旧要点"],
                "speaker_notes": "",
            }
        ],
    }
    out = await refine_slide_deck(
        deck,
        target_slide_indexes=[1],
        instructions="随便改",
        llm=FakeRefineLLM(),
        locks={1: ["title"]},
        max_repair_attempts=2,
    )
    assert out["slides"][0]["title"] == "旧标题"
    texts = [bullet_parts(b)[0] for b in out["slides"][0]["bullets"]]
    assert "新要点" in texts
