# 时间：2026-03-22；理由：意图解读模块的 JSON 解析须可回归；方法：不调用真实 LLM，只测 parse_* 
from __future__ import annotations

import json

from backend.core.agent.intent_interpreter import (
    WritingInstructionIntent,
    format_intent_for_writing_prompt,
    parse_explain_intent_json,
    parse_revision_judgment_json,
)


def test_parse_explain_intent_json_plain():
    raw = json.dumps(
        {
            "intent_summary": "开篇用个人经历",
            "revision_scope": "opening_only",
            "must_preserve_substance": ["师哥", "写什么比怎么写重要"],
            "stylistic_constraints": ["第一人称"],
            "ambiguity_notes": "",
        },
        ensure_ascii=False,
    )
    r = parse_explain_intent_json(raw)
    assert r.revision_scope == "opening_only"
    assert len(r.must_preserve_substance) == 2


def test_parse_explain_intent_json_fenced():
    raw = '```json\n{"intent_summary":"x","revision_scope":"unclear","must_preserve_substance":[],"stylistic_constraints":[],"ambiguity_notes":""}\n```'
    r = parse_explain_intent_json(raw)
    assert r.intent_summary == "x"


def test_format_intent_for_writing_prompt_contains_fields():
    # 时间：2026-03-13；理由：编排注入块格式须稳定可回归；方法：断言关键前缀与字段行
    intent = WritingInstructionIntent(
        intent_summary="改开篇",
        revision_scope="opening_only",
        must_preserve_substance=["A", "B"],
        stylistic_constraints=["第一人称"],
        ambiguity_notes="无",
    )
    block = format_intent_for_writing_prompt(intent)
    assert "【系统解读·用户写作意图】" in block
    assert "改开篇" in block
    assert "opening_only" in block
    assert "A" in block and "B" in block
    assert "第一人称" in block


def test_parse_revision_judgment_json():
    raw = json.dumps(
        {
            "satisfied": False,
            "confidence": "high",
            "rationale": "未写经历",
            "unmet_points": ["缺师哥叙事"],
        },
        ensure_ascii=False,
    )
    j = parse_revision_judgment_json(raw)
    assert j.satisfied is False
    assert "师哥" in j.unmet_points[0]
