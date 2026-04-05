"""
写作助手编排侧策略（是否注入 doc-coauthoring 规划段等）。

时间：2026-04-04；理由：与 article_writing_message_contract 解耦——契约文件只负责「参考块 + 用户句」及写作类 user 注入片段的字面规则；
本模块负责 stream_process 分支上的 workflow 判定，避免「消息格式」与「会话工作流」混在同一文件。

方法：orchestrator / replay_cli 从此导入 task_triggers_doc_coauthoring；关键词列表已置空，仅 session.metadata.workflow 显式开启。
"""
from __future__ import annotations

from typing import Optional

# 时间：2026-04-04；理由：产品收窄为公众号长文新写/改稿；方法：置空，保留元组便于将来若需再启用关键词时有单一修改点
DOC_COAUTHORING_TRIGGER_KEYWORDS: tuple[str, ...] = ()


def task_triggers_doc_coauthoring(
    task: str,
    *,
    session_workflow: Optional[str] = None,
) -> bool:
    """
    与 orchestrator.stream_process 写作分支一致：
    True 当且仅当 session.metadata.workflow == doc_coauthoring（或未来 DOC_COAUTHORING_TRIGGER_KEYWORDS 非空且 task 命中）。
    task 参数保留用于关键词扩展，当前关键词列表为空故仅 workflow 生效。
    """
    if (session_workflow or "").strip() == "doc_coauthoring":
        return True
    t = task or ""
    return any(kw in t for kw in DOC_COAUTHORING_TRIGGER_KEYWORDS)
