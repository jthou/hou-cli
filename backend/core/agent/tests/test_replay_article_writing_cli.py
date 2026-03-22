"""
replay_article_writing_cli：compute_article_writing_prompts 与编排对齐（不调 LLM）。
时间：2026-03-21；理由：CLI 内 prompt 预览；方法：importlib 加载 scripts 下模块。
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def replay_mod():
    path = ROOT / "scripts" / "replay_article_writing_cli.py"
    spec = importlib.util.spec_from_file_location("replay_article_writing_cli", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_compute_article_writing_prompts_contains_writing_assistant(replay_mod):
    from backend.core.agent.article_writing_message_contract import build_message_for_model

    task = build_message_for_model([], "仅测 prompt")
    system, user, use_doc = replay_mod.compute_article_writing_prompts(task)
    assert "写作助手" in system
    assert use_doc is False
    assert "仅测 prompt" in user


def test_doc_coauthoring_keyword_triggers_planning(replay_mod):
    task = "我要写PRD，请列大纲"
    system, _user, use_doc = replay_mod.compute_article_writing_prompts(task)
    assert use_doc is True
    assert "阶段一" in system or "上下文收集" in system


def test_reference_args_to_blocks_skips_sentinels(replay_mod):
    assert replay_mod.reference_args_to_blocks(["（无）", "(无)"]) == []
    assert replay_mod.reference_args_to_blocks(None) == []
