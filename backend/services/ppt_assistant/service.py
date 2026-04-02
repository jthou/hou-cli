"""PPT 助手核心：extract / deck / pipeline（供 HTTP 与 CLI 共用）。"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional, TypeVar

from backend.services.ppt_assistant.chunking import chunk_text
from backend.services.ppt_assistant.deck_normalize import enforce_single_slide_deck
from backend.services.ppt_assistant.json_extract import parse_llm_json_object
from backend.services.ppt_assistant import prompts

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _empty_ppt_elements(meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    m = dict(meta or {})
    return {
        "version": 1,
        "meta": {
            "source_hint": m.get("source_hint", ""),
            "audience": m.get("audience", ""),
            "constraints_note": m.get("constraints_note", ""),
            "user_requirements": m.get("user_requirements", ""),
        },
        "one_liner": "",
        "takeaway": "",
        "outline_sections": [],
        "highlight_numbers": [],
        "terms": [],
        "layout_hints": [],
    }


def _normalize_meta(meta: Optional[Dict[str, Any]]) -> str:
    if not meta:
        return ""
    parts = []
    for k in (
        "audience",
        "constraints_note",
        "user_requirements",
        "source_hint",
        "max_slides_hint",
    ):
        v = meta.get(k)
        if v:
            parts.append(f"{k}: {v}")
    return "\n".join(parts)


async def _llm_chat_json(
    llm_chat: Callable[..., Any],
    *,
    system_prompt: str,
    user_prompt: str,
    audit_source: str,
) -> Dict[str, Any]:
    response = await llm_chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        audit_meta={"source": audit_source},
    )
    if not isinstance(response, str):
        raise ValueError("llm returned non-string")
    return parse_llm_json_object(response)


async def extract_ppt_elements(
    article: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    llm: Any,
    chunk_chars: int = 10_000,
    overlap: int = 400,
) -> Dict[str, Any]:
    """
    长文 → ppt_elements。超过 chunk_chars 时分块抽取再合并。
    llm: LLMService 实例，须提供 async chat(system_prompt=, user_prompt=, audit_meta=).
    """
    meta_note = _normalize_meta(meta)
    article = (article or "").strip()
    if not article:
        return _empty_ppt_elements(meta)

    async def chat(**kw):
        return await llm.chat(**kw)

    if len(article) <= chunk_chars:
        user = prompts.extract_user(article, meta_note)
        data = await _llm_chat_json(
            chat,
            system_prompt=prompts.EXTRACT_SYSTEM,
            user_prompt=user,
            audit_source="ppt_assistant_extract",
        )
        _ensure_version(data)
        if meta:
            data.setdefault("meta", {})
            if isinstance(data["meta"], dict):
                data["meta"].setdefault(
                    "constraints_note", str(meta.get("constraints_note", ""))
                )
                data["meta"].setdefault(
                    "user_requirements", str(meta.get("user_requirements", ""))
                )
        return data

    chunks = chunk_text(article, chunk_chars, overlap)
    partial_objects: list[Dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        user = prompts.extract_partial_user(ch, i, len(chunks), meta_note)
        partial = await _llm_chat_json(
            chat,
            system_prompt=prompts.EXTRACT_PARTIAL_SYSTEM,
            user_prompt=user,
            audit_source="ppt_assistant_extract_partial",
        )
        partial["chunk_index"] = i
        partial_objects.append(partial)

    merged_blob = json.dumps(partial_objects, ensure_ascii=False, indent=2)
    user_merge = prompts.merge_user(merged_blob, meta_note)
    merged = await _llm_chat_json(
        chat,
        system_prompt=prompts.MERGE_SYSTEM,
        user_prompt=user_merge,
        audit_source="ppt_assistant_merge",
    )
    _ensure_version(merged)
    return merged


def _ensure_version(data: Dict[str, Any]) -> None:
    if int(data.get("version", 1)) != 1:
        logger.warning("ppt_assistant: unexpected version %s", data.get("version"))


async def generate_slide_deck(
    ppt_elements: Dict[str, Any],
    *,
    constraints: Optional[str] = None,
    llm: Any,
    single_slide: bool = True,
    user_requirements: Optional[str] = None,
) -> Dict[str, Any]:
    """ppt_elements → slide_deck。默认 **单张幻灯片**（一张上展示关键元素）。"""
    async def chat(**kw):
        return await llm.chat(**kw)

    blob = json.dumps(ppt_elements, ensure_ascii=False, indent=2)
    system = (
        prompts.DECK_SYSTEM_SINGLE if single_slide else prompts.DECK_SYSTEM_MULTI
    )
    user = prompts.deck_user(
        blob,
        constraints or "",
        single_slide=single_slide,
        user_requirements=user_requirements or "",
    )
    deck = await _llm_chat_json(
        chat,
        system_prompt=system,
        user_prompt=user,
        audit_source="ppt_assistant_deck",
    )
    if int(deck.get("version", 1)) != 1:
        logger.warning("slide_deck unexpected version %s", deck.get("version"))
    if single_slide:
        deck = enforce_single_slide_deck(deck)
    return deck


async def run_ppt_pipeline(
    article: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    deck_constraints: Optional[str] = None,
    llm: Any,
    chunk_chars: int = 10_000,
    overlap: int = 400,
    elements_only: bool = False,
    single_slide: bool = True,
) -> Dict[str, Any]:
    """extract → deck 一步完成（与 UI「运行」一致）。默认单页 deck。"""
    elements = await extract_ppt_elements(
        article, meta=meta, llm=llm, chunk_chars=chunk_chars, overlap=overlap
    )
    if elements_only:
        return {"ppt_elements": elements, "slide_deck": None}
    ur = ""
    if meta:
        ur = str(meta.get("user_requirements") or "").strip()
    deck = await generate_slide_deck(
        elements,
        constraints=deck_constraints,
        llm=llm,
        single_slide=single_slide,
        user_requirements=ur or None,
    )
    return {"ppt_elements": elements, "slide_deck": deck}
