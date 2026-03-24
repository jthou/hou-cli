"""
general_chat 上下文注入：已完成任务队列摘要（支持按当前问题关键词相关性优先）。

时间：2026-03-13；理由：用户要求综合历史/任务/联网；初版仅按时间倒序取 N 条；
时间：2026-03-14；理由：用户希望「快速找到和问题相关的」任务；方法：扩大候选池 + 与 hybrid 一致的 query 截取 + 中英混合关键词/子串/双字元打分，取 Top-K，无命中时回退最近完成并写明说明。
时间：2026-03-14；理由：用户要求 SQLite FTS5；方法：TaskQueueDB.search_completed_tasks_fts（bm25）优先，不足条数补最近完成；FTS 无结果或关闭时回退 POOL+关键词打分。

环境：
- GENERAL_CHAT_INJECT_COMPLETED_TASKS（默认 true）
- GENERAL_CHAT_COMPLETED_TASKS_LIMIT：最终注入条数（1–50，默认 15）
- GENERAL_CHAT_COMPLETED_TASKS_RELEVANCE：是否启用相关性排序（默认 true；false=仅时间倒序取 LIMIT 条）
- GENERAL_CHAT_COMPLETED_TASKS_POOL：启用相关性时先拉取候选条数（默认 80，上限 200）
- GENERAL_CHAT_COMPLETED_TASKS_USE_FTS：是否优先走 FTS5（默认 true；需 SQLite 编译 ENABLE_FTS5；false=仅用关键词打分）

明确兜底：拉库异常时返回空串；相关性模式下若全部得分为 0，回退为「最近完成」前 N 条并加一行说明（时间/理由/方法见 rank_completed_tasks_for_query）。
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 与 hybrid_history._query_for_retrieval 对齐：长参考块里只取「用户本次提问」后段作检索 query，避免稀释。
_MARKER_USER_Q = "【用户本次提问】"


def _query_for_completed_tasks(task: str) -> str:
    t = (task or "").strip()
    if _MARKER_USER_Q in t:
        tail = t.split(_MARKER_USER_Q, 1)[-1].strip()
        if tail:
            return tail[:4000]
    return t[:4000]


def _truncate(s: str, max_len: int) -> str:
    t = (s or "").replace("\n", " ").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _haystack_for_task(t: Dict[str, Any]) -> str:
    parts = [
        str(t.get("task_name") or ""),
        str(t.get("task_type") or ""),
        str(t.get("result_summary") or ""),
        str(t.get("message") or ""),
    ]
    return "\n".join(parts).lower()


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def score_completed_task_relevance(task: Dict[str, Any], query: str) -> int:
    """
    轻量相关性：无额外依赖；英文按空白分词，中文整句子串命中加权 + 双字滑动窗口命中计数。
    与 KeywordRetrievalEngine 同属「关键词层」，后续可换向量检索而不改调用方。
    """
    q = (query or "").strip().lower()
    if not q:
        return 0
    hay = _haystack_for_task(task)
    if not hay:
        return 0
    score = 0
    # 整句命中（短中文问句很有效）
    if len(q) >= 2 and q in hay:
        score += 12
    # 英文/数字 token（长度>=2）
    for w in re.findall(r"[a-z0-9]{2,}", q):
        if w in hay:
            score += 4
    # 空白分词（中英混排时）
    for w in q.split():
        w = w.strip()
        if len(w) >= 2 and w in hay:
            score += 3
    # 中文无空格时：双字元在 hay 中出现则计分（控制窗口长度）
    if " " not in q and _CJK_RE.search(q):
        max_win = min(len(q), 24)
        for i in range(max_win - 1):
            big = q[i : i + 2]
            if _CJK_RE.search(big) and big in hay:
                score += 1
    return score


def rank_completed_tasks_for_query(
    tasks: List[Dict[str, Any]],
    query: str,
    *,
    top_k: int,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    按相关性排序取前 top_k。

    返回 (selected_tasks, used_relevance_fallback)。后者为 True 表示所有得分均为 0，
    已回退为「原列表顺序」的前 top_k（list_tasks 为 created_at DESC，即最近完成）。

    时间：2026-03-14；理由：无命中时仍给模型最近任务上下文，避免空白；方法：得分全 0 时切片 tasks[:top_k]。
    """
    q = (query or "").strip()
    if not tasks or not q:
        return tasks[:top_k], False

    indexed: List[Tuple[int, int, Dict[str, Any]]] = []
    for i, t in enumerate(tasks):
        s = score_completed_task_relevance(t, q)
        indexed.append((s, i, t))

    max_s = max((x[0] for x in indexed), default=0)
    if max_s == 0:
        # 明确兜底：与当前问题无字段级重叠时仍提供最近完成记录，避免上下文断档
        return tasks[:top_k], True

    indexed.sort(key=lambda x: (-x[0], x[1]))
    return [x[2] for x in indexed[:top_k]], False


def format_completed_tasks_lines(tasks: List[Dict[str, Any]], *, summary_max: int = 200) -> str:
    """将 list_tasks 返回的字典列表格式化为可读文本（供单测断言）。"""
    lines: List[str] = []
    for i, t in enumerate(tasks, start=1):
        tid = t.get("task_id") or ""
        name = t.get("task_name") or ""
        ttype = t.get("task_type") or ""
        done = t.get("completed_at") or ""
        summ = t.get("result_summary") or ""
        msg = t.get("message") or ""
        piece = _truncate(summ, summary_max) if summ else _truncate(msg, summary_max)
        lines.append(
            f"{i}. task_id={tid} | type={ttype} | name={name} | completed_at={done}"
            + (f"\n   摘要/消息: {piece}" if piece else "")
        )
    return "\n".join(lines)


def _default_fetch_completed(limit: int) -> List[Dict[str, Any]]:
    """默认从 SQLite 任务队列拉取；单测可注入替代实现，避免导入链依赖 chromadb 等。"""
    from backend.infrastructure.storage.task_queue_db import (
        TaskStatus,
        get_task_queue_db,
    )

    db = get_task_queue_db()
    return db.list_tasks(status=TaskStatus.COMPLETED, limit=limit, offset=0)


def build_completed_tasks_reference_block(
    *,
    current_user_query: Optional[str] = None,
    _fetch_completed: Optional[Callable[[int], List[Dict[str, Any]]]] = None,
) -> str:
    """
    返回可拼入 user_prompt 的「已完成任务」块；无数据或失败时返回空串。

    current_user_query: 当前用户自然语言问题，用于相关性排序；不传则不做相关性（等价于仅时间序，在 RELEVANCE=true 时仍会用空 query 打分全 0 而回退——故务必由 Orchestrator 传入 task）。

    _fetch_completed: 可选注入 (limit) -> tasks，仅用于测试或定制数据源。
    """
    if os.getenv("GENERAL_CHAT_INJECT_COMPLETED_TASKS", "true").lower() != "true":
        return ""
    try:
        lim = int(os.getenv("GENERAL_CHAT_COMPLETED_TASKS_LIMIT", "15"))
    except ValueError:
        lim = 15
    lim = max(1, min(50, lim))

    relevance = os.getenv("GENERAL_CHAT_COMPLETED_TASKS_RELEVANCE", "true").lower() == "true"
    try:
        pool = int(os.getenv("GENERAL_CHAT_COMPLETED_TASKS_POOL", "80"))
    except ValueError:
        pool = 80
    pool = max(lim, min(200, pool))

    fetch = _fetch_completed or _default_fetch_completed
    q = _query_for_completed_tasks(current_user_query or "")

    use_fts = (
        _fetch_completed is None
        and os.getenv("GENERAL_CHAT_COMPLETED_TASKS_USE_FTS", "true").lower() == "true"
        and relevance
        and q.strip()
    )

    selected: List[Dict[str, Any]] = []
    fallback_recent = False
    fts_mode = False

    try:
        if use_fts:
            from backend.infrastructure.storage.task_queue_db import get_task_queue_db

            db = get_task_queue_db()
            try:
                fts_hits = db.search_completed_tasks_fts(q, limit=lim)
            except Exception as ex:
                logger.warning("completed_tasks_prompt: FTS 查询异常，回退关键词排序: %s", ex)
                fts_hits = []
            if fts_hits:
                seen = {t.get("task_id") for t in fts_hits if t.get("task_id")}
                need = lim - len(fts_hits)
                more = (
                    db.list_completed_tasks_excluding_ids(seen, limit=need)
                    if need > 0
                    else []
                )
                selected = (fts_hits + more)[:lim]
                fts_mode = True

        if not selected:
            if relevance and q.strip():
                raw = fetch(pool)
                selected, fallback_recent = rank_completed_tasks_for_query(raw, q, top_k=lim)
            else:
                selected = fetch(lim)
                fallback_recent = False
    except Exception as e:
        logger.warning("completed_tasks_prompt: 拉取已完成任务失败，跳过注入: %s", e)
        return ""

    if not selected:
        return ""

    body = format_completed_tasks_lines(selected)
    if fts_mode:
        strat = ""
        title = "【已完成任务（任务队列，FTS5 bm25 优先；条数不足时按时间补位）】\n"
    elif relevance and q.strip():
        if fallback_recent:
            strat = (
                "【说明】与当前问题在任务名称/类型/摘要/消息中未匹配到关键词；"
                "以下为最近完成的记录供参考（按时间）。\n"
            )
            title = "【已完成任务（任务队列，最近完成 · 无相关性命中时的回退）】\n"
        else:
            strat = ""
            title = "【已完成任务（任务队列，按与当前问题的相关性优先 · 关键词打分）】\n"
    else:
        strat = ""
        title = "【已完成任务（任务队列，按创建时间倒序）】\n"

    return (
        f"{strat}{title}"
        "以下仅供复盘与引用；回答时若用到某条请标明 task_id。\n"
        f"{body}\n"
    )
