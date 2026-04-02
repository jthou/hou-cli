"""
PPT 助手 CLI：用固定教材节选 fixture 验证 extract / run 与 service 一致（mock LLM）。

真实百炼验证（可选）:
  export BAILIAN_API_KEY=...  # 或 DASHSCOPE_API_KEY
  pytest tests/test_ppt_assistant_cli.py -m ppt_assistant_live -s
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from backend.cli.ppt_assistant_cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "ppt_assistant_lm_section_1_1.txt"

MINIMAL_ELEMENTS_JSON = (
    '{"version":1,"meta":{"source_hint":"","audience":"","constraints_note":""},'
    '"one_liner":"语言模型对文本概率建模","takeaway":"从 n-gram 到 PLM 与大模型",'
    '"outline_sections":[{"id":"1","title":"链式法则与 n-gram","summary":"公式分解",'
    '"key_claims":[{"claim":"联合概率分解为条件概率积","bullets":["式(1.1)"],"evidence_quotes":[],"speaker_elaboration":""}]}],'
    '"highlight_numbers":[],"terms":[],"layout_hints":[]}'
)

MINIMAL_DECK_JSON = (
    '{"version":1,"deck_title":"大语言模型基本概念",'
    '"slides":['
    '{"index":1,"kind":"title","title":"1.1 大语言模型","bullets":[],"speaker_notes":""},'
    '{"index":2,"kind":"content","title":"语言模型","bullets":["概率分布","n-gram"],"speaker_notes":""}'
    "]}"
)


class FakeLLMSingleExtract:
    """8653 字 fixture < 默认 chunk 10000 → 仅 extract +（run 时）deck。"""

    def __init__(self, *args, **kwargs):
        """与 LLMService(...) 构造兼容。"""

    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        src = (audit_meta or {}).get("source", "")
        if src == "ppt_assistant_extract":
            return MINIMAL_ELEMENTS_JSON
        if src == "ppt_assistant_deck":
            return MINIMAL_DECK_JSON
        raise AssertionError(f"unexpected source: {src}")


class FakeLLMChunked:
    """小 chunk → partial × N + merge + deck。"""

    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, system_prompt="", user_prompt="", messages=None, audit_meta=None, **kw):
        src = (audit_meta or {}).get("source", "")
        if src == "ppt_assistant_extract_partial":
            return (
                '{"chunk_index":0,"outline_sections":[],"highlight_numbers":[],"terms":[]}'
            )
        if src == "ppt_assistant_merge":
            return MINIMAL_ELEMENTS_JSON
        if src == "ppt_assistant_deck":
            return MINIMAL_DECK_JSON
        if src == "ppt_assistant_extract":
            return MINIMAL_ELEMENTS_JSON
        raise AssertionError(f"unexpected source: {src}")


@pytest.fixture
def lm_article_text():
    assert FIXTURE.is_file(), f"missing fixture {FIXTURE}"
    return FIXTURE.read_text(encoding="utf-8")


def test_fixture_is_substantial(lm_article_text):
    """用户提供的一节正文：仓库内完整 fixture 约 8.6k 字；含公式与术语。"""
    assert len(lm_article_text) >= 3500, "fixture 过短时请同步 tests/fixtures/ppt_assistant_lm_section_1_1.txt"
    assert "语言模型" in lm_article_text
    assert "n-gram" in lm_article_text or "元语法" in lm_article_text
    assert "GPT" in lm_article_text or "BERT" in lm_article_text


def test_cli_extract_with_lm_fixture(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.services.llm.llm_service.LLMService", FakeLLMSingleExtract)
    runner = CliRunner()
    out = tmp_path / "elements.json"
    result = runner.invoke(
        main,
        ["extract", "-i", str(FIXTURE), "-o", str(out)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "ppt_elements" in data
    assert data["ppt_elements"]["version"] == 1
    assert "one_liner" in data["ppt_elements"]


def test_cli_run_with_lm_fixture_chunked(monkeypatch, tmp_path):
    """强制 --chunk-chars 2000，走 partial → merge → deck，覆盖长文分支。"""
    monkeypatch.setattr("backend.services.llm.llm_service.LLMService", FakeLLMChunked)
    runner = CliRunner()
    out_dir = tmp_path / "ppt_out"
    result = runner.invoke(
        main,
        [
            "run",
            "-i",
            str(FIXTURE),
            "-d",
            str(out_dir),
            "--chunk-chars",
            "2000",
            "--overlap",
            "200",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert (out_dir / "ppt_elements.json").is_file()
    assert (out_dir / "slide_deck.json").is_file()
    assert (out_dir / "slide_deck.md").is_file()
    deck = json.loads((out_dir / "slide_deck.json").read_text(encoding="utf-8"))
    assert deck["deck_title"] == "大语言模型基本概念"
    md = (out_dir / "slide_deck.md").read_text(encoding="utf-8")
    assert "第 1 页" in md


@pytest.mark.ppt_assistant_live
@pytest.mark.asyncio
async def test_live_extract_smoke_if_api_configured(lm_article_text):
    """
    需可用的百炼密钥；仅作手工/CI 可选烟测，默认不打 API。
    """
    import os

    if not (
        os.environ.get("BAILIAN_API_KEY")
        or os.environ.get("DASHSCOPE_API_KEY")
    ):
        pytest.skip("未配置 BAILIAN_API_KEY / DASHSCOPE_API_KEY")

    from backend.services.llm.llm_service import LLMService
    from backend.services.ppt_assistant import extract_ppt_elements

    llm = LLMService(temperature=0.35)
    # 单篇仍较长，控制成本：只用前 3500 字做烟测
    snippet = lm_article_text[:3500]
    elements = await extract_ppt_elements(
        snippet,
        meta={"constraints_note": "测试：教材 1.1 节选，输出精简 ppt_elements"},
        llm=llm,
        chunk_chars=50_000,
        overlap=400,
    )
    assert isinstance(elements, dict)
    assert elements.get("version") == 1
    assert elements.get("outline_sections") is not None
    assert len(elements.get("one_liner", "")) > 0
