"""
混合会话历史：最近若干条全保留 + 更早消息按关键词与当前问题检索，减少无关历史噪声。

时间：2026-03-13；理由：work_assistant/general_chat 曾全量拼接历史；方法：KeywordRetrievalEngine 检索旧段 + 时间序合并；
可观测性：返回 meta 供 __CTX_META__ 下发前端展示（非「模型思维链」，仅为编排选中的消息摘要）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from backend.core.context.models import Message, MessageRole
from backend.core.context.retrieval.base import RetrievalEngine


def _query_for_retrieval(task: str) -> str:
    """优先用「用户本次提问」正文，避免参考块过长稀释关键词。"""
    marker = "【用户本次提问】"
    t = (task or "").strip()
    if marker in t:
        tail = t.split(marker, 1)[-1].strip()
        if tail:
            return tail[:4000]
    return t[:4000]


def select_hybrid_chat_messages(
    messages: List[Message],
    query: str,
    retrieval: RetrievalEngine,
    *,
    recent_message_count: int,
    retrieve_top_k: int,
) -> Tuple[List[Message], Dict[str, Any]]:
    """
    返回 (按时间序选中的消息, 供前端展示的 meta)。

    - 消息数 <= recent_message_count：全部使用，strategy=all。
    - 否则：末尾 recent_message_count 条必保留；更早的中用 retrieval.search 取 top_k，再按原序合并。
    """
    filtered: List[Message] = [
        m for m in messages if m.role in (MessageRole.USER, MessageRole.ASSISTANT)
    ]
    n = len(filtered)
    q = _query_for_retrieval(query)

    if n <= recent_message_count:
        items = _build_meta_items(filtered, list(range(n)), set(), n, recent_message_count)
        meta: Dict[str, Any] = {
            "type": "context_selection",
            "v": 1,
            "strategy": "all",
            "total_in_session": n,
            "recent_tail_kept": n,
            "retrieve_top_k": retrieve_top_k,
            "retrieved_hits": 0,
            "used_count": n,
            "query_preview": (q[:160] + "…") if len(q) > 160 else q,
            "items": items,
        }
        return filtered, meta

    recent_start = n - recent_message_count
    recent_slice = filtered[recent_start:]
    old_slice = filtered[:recent_start]
    retrieved: List[Message] = (
        retrieval.search(old_slice, q, top_k=retrieve_top_k) if old_slice and q.strip() else []
    )

    id_to_index = {id(m): i for i, m in enumerate(filtered)}
    indices: set[int] = set(range(recent_start, n))
    retrieved_ids: set[int] = set()
    for m in retrieved:
        j = id_to_index.get(id(m))
        if j is not None:
            indices.add(j)
            retrieved_ids.add(id(m))

    sorted_idx = sorted(indices)
    chosen = [filtered[i] for i in sorted_idx]
    items = _build_meta_items(chosen, sorted_idx, retrieved_ids, n, recent_message_count)

    meta = {
        "type": "context_selection",
        "v": 1,
        "strategy": "hybrid",
        "total_in_session": n,
        "recent_tail_kept": recent_message_count,
        "retrieve_top_k": retrieve_top_k,
        "retrieved_hits": len(retrieved),
        "used_count": len(chosen),
        "query_preview": (q[:160] + "…") if len(q) > 160 else q,
        "items": items,
    }
    return chosen, meta


def _build_meta_items(
    chosen: List[Message],
    sorted_indices: List[int],
    retrieved_ids: set[int],
    n: int,
    recent_message_count: int,
) -> List[Dict[str, Any]]:
    recent_start = n - recent_message_count
    out: List[Dict[str, Any]] = []
    for msg, idx in zip(chosen, sorted_indices):
        rid = id(msg)
        if idx >= recent_start:
            src = "recent_tail"
        elif rid in retrieved_ids:
            src = "keyword_hit"
        else:
            src = "recent_tail"
        prev = (msg.content or "").replace("\n", " ").strip()
        if len(prev) > 120:
            prev = prev[:118] + "…"
        out.append(
            {
                "role": msg.role.value,
                "source": src,
                "preview": prev,
                "message_id": msg.message_id,
                "index": idx,
            }
        )
    return out


def messages_to_llm_turns(messages: List[Message]) -> List[Dict[str, str]]:
    """与 get_messages_for_llm 一致的 role/content 列表。"""
    return [{"role": m.role.value, "content": m.content or ""} for m in messages]
