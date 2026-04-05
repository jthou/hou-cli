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


def test_doc_coauthoring_keywords_do_not_trigger_planning(replay_mod):
    """收窄后 PRD 等关键词不再注入 DOC_COAUTHORING_WORKFLOW。"""
    task = "我要写PRD，请列大纲"
    system, _user, use_doc = replay_mod.compute_article_writing_prompts(task)
    assert use_doc is False
    assert "阶段一" not in system and "上下文收集" not in system


def test_doc_coauthoring_session_workflow_triggers_planning(replay_mod):
    task = "列大纲"
    system, _user, use_doc = replay_mod.compute_article_writing_prompts(
        task, session_workflow="doc_coauthoring"
    )
    assert use_doc is True
    assert "阶段一" in system or "上下文收集" in system


def test_reference_args_to_blocks_skips_sentinels(replay_mod):
    assert replay_mod.reference_args_to_blocks(["（无）", "(无)"]) == []
    assert replay_mod.reference_args_to_blocks(None) == []


def test_compute_prompts_with_draft_and_revision_injection_matches_orchestrator_intent(replay_mod):
    """局部改稿 fixture：须含改稿范围、草稿正文、修改意见落实注入（与 orchestrator 写作分支一致）。"""
    from backend.core.agent.article_writing_message_contract import build_message_for_model

    draft_path = ROOT / "scripts" / "fixtures" / "writing_replay" / "draft_local_edit.md"
    q_path = ROOT / "scripts" / "fixtures" / "writing_replay" / "question_local_edit.txt"
    draft = draft_path.read_text(encoding="utf-8")
    user_q = q_path.read_text(encoding="utf-8").strip()
    base_task = build_message_for_model([], user_q)
    system, user, _ = replay_mod.compute_article_writing_prompts(base_task, current_article=draft)
    assert "写作助手" in system
    assert "【改稿范围（须遵守）】" in user
    assert "【当前文章（右侧草稿）】" in user
    assert "苏格拉底" in user  # 草稿进入 user
    assert "系统检出·修改意见落实" in user
    assert "局部优先" in user or "禁止" in user
