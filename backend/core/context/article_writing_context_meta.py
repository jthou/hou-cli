"""
写作助手流式可观测性：__CTX_META__ 描述本轮并入 user 提示的素材（非会话聊天历史）。

时间：2026-03-13；理由：前端 ContextSelectionPanel 在 article_writing 需真实数据；写作策略本就不注入多轮 chat，
     与 hybrid 的「选历史」不同，故单独 strategy=article_writing，避免误读为「选了消息进模型」。
方法：orchestrator 在拼完 user_prompt 后调用 build_article_writing_stream_ctx_meta 并 yield build_ctx_meta；
     开关 ENABLE_ARTICLE_WRITING_CTX_META（默认 true，可关）。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def _preview_text(s: str, n: int = 120) -> str:
    t = (s or "").replace("\n", " ").strip()
    if len(t) > n:
        return t[: n - 1] + "…"
    return t or "（空）"


def _user_question_excerpt(raw_task: str) -> str:
    """与 hybrid_history._query_for_retrieval 一致：优先【用户本次提问】后段。"""
    marker = "【用户本次提问】"
    t = (raw_task or "").strip()
    if marker in t:
        tail = t.split(marker, 1)[-1].strip()
        if tail:
            return tail
    return t


def task_contains_reference_blocks(raw_task: str) -> bool:
    """与 article_writing_message_contract 对齐：有参考时 task 含【参考n】或标准参考引言。"""
    t = raw_task or ""
    return "【参考" in t or "以下是用户提供的参考资料" in t


def build_article_writing_stream_ctx_meta(
    *,
    session_chat_turn_count: int,
    raw_task: str,
    has_draft_injection: bool,
    draft_char_count: int,
    draft_text_preview: str,
    has_reference_blocks: bool,
    has_profile_injection: bool,
    profile_preview: str,
    has_word_count_hint: bool,
    has_section_hint: bool,
) -> Dict[str, Any]:
    """构造与 StreamMessageBuilder.build_ctx_meta 兼容的 dict。"""
    q = _user_question_excerpt(raw_task)
    query_preview = _preview_text(q, 160)

    items: List[Dict[str, Any]] = []
    idx = 0

    if has_draft_injection:
        extra = ""
        if (draft_text_preview or "").strip():
            extra = "：" + _preview_text(draft_text_preview.strip(), 72)
        items.append(
            {
                "display_role": "草稿",
                "role": "user",
                "source": "injected_draft",
                "preview": _preview_text(
                    f"已注入右侧当前文章为改稿锚点（约 {max(0, int(draft_char_count))} 字）{extra}",
                    200,
                ),
                "message_id": None,
                "index": idx,
            }
        )
        idx += 1

    if has_reference_blocks:
        items.append(
            {
                "display_role": "参考",
                "role": "user",
                "source": "injected_reference",
                "preview": "用户提供的参考块已并入本条消息（与 Web 参考面板一致）",
                "message_id": None,
                "index": idx,
            }
        )
        idx += 1

    if has_profile_injection and (profile_preview or "").strip():
        items.append(
            {
                "display_role": "画像",
                "role": "user",
                "source": "injected_profile",
                "preview": _preview_text(f"写作画像已并入：{profile_preview.strip()}", 200),
                "message_id": None,
                "index": idx,
            }
        )
        idx += 1

    if has_word_count_hint:
        items.append(
            {
                "display_role": "系统",
                "role": "user",
                "source": "injected_constraints",
                "preview": "已注入【系统检出·用户字数要求】",
                "message_id": None,
                "index": idx,
            }
        )
        idx += 1

    if has_section_hint:
        items.append(
            {
                "display_role": "系统",
                "role": "user",
                "source": "injected_constraints",
                "preview": "已注入【系统检出·长文版式】",
                "message_id": None,
                "index": idx,
            }
        )
        idx += 1

    items.append(
        {
            "display_role": "指令",
            "role": "user",
            "source": "user_turn",
            "preview": _preview_text(q, 200),
            "message_id": None,
            "index": idx,
        }
    )

    return {
        "type": "context_selection",
        "v": 1,
        "strategy": "article_writing",
        "total_in_session": max(0, int(session_chat_turn_count)),
        "recent_tail_kept": 0,
        "retrieve_top_k": 0,
        "retrieved_hits": 0,
        "used_count": len(items),
        "query_preview": query_preview,
        "items": items,
        "article_writing_note": "会话内聊天记录未注入模型；上列为并入本次 user 提示的素材摘要。",
    }


def parse_first_ctx_meta_payload_from_stream_chunks(chunks: list) -> Optional[Dict[str, Any]]:
    """从流式 chunk 列表中解析第一条 `__CTX_META__:` 的 JSON 对象。

    时间：2026-03-13；理由：编排层与 CLI 脚本共用同一解析；方法：与 stream_sender.build_ctx_meta 前缀对齐。
    """
    for c in chunks:
        if isinstance(c, str) and c.startswith("__CTX_META__:"):
            try:
                return json.loads(c.split(":", 1)[1].strip())
            except (json.JSONDecodeError, TypeError, ValueError):
                return None
    return None


def validate_article_writing_ctx_meta_response(
    payload: Optional[Dict[str, Any]],
    *,
    expect_reference: bool = True,
) -> Tuple[bool, str]:
    """供 CLI/脚本验收：是否为写作策略且（可选）含参考块项。

    时间：2026-03-13；理由：与 scripts/test_article_writing_opening_rewrite.py 去重；方法：纯函数 + 单测。
    """
    if payload is None:
        return (
            False,
            "[ctx-meta] 未发现可解析的 __CTX_META__ 帧。若故意关闭，请检查 ENABLE_ARTICLE_WRITING_CTX_META=true。",
        )
    if payload.get("strategy") != "article_writing":
        return False, f"[ctx-meta] strategy 非 article_writing: {payload.get('strategy')!r}"
    sources = {it.get("source") for it in (payload.get("items") or []) if isinstance(it, dict)}
    if expect_reference and "injected_reference" not in sources:
        return (
            False,
            f"[ctx-meta] 当前校验要求 items 含 injected_reference；实际 sources={sources}",
        )
    ok_msg = "[ctx-meta] 通过：strategy=article_writing"
    if expect_reference:
        ok_msg += "，且含参考块说明（injected_reference）。"
    else:
        ok_msg += "。"
    return True, ok_msg
