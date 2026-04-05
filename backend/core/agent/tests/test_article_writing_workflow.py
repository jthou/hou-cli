# 时间：2026-04-04；理由：task_triggers_doc_coauthoring 迁至 article_writing_workflow；方法：独立单测
from backend.core.agent.article_writing_workflow import task_triggers_doc_coauthoring


def test_task_triggers_doc_coauthoring():
    assert task_triggers_doc_coauthoring("随便") is False
    assert task_triggers_doc_coauthoring("写PRD大纲") is False
    assert task_triggers_doc_coauthoring("", session_workflow="doc_coauthoring") is True
