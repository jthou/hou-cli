"""PPT 助手核心：extract / deck / pipeline / refine（供 HTTP 与 CLI 共用）。"""

from __future__ import annotations

import copy
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar

from backend.services.ppt_assistant.chunking import chunk_text
from backend.services.ppt_assistant.deck_normalize import enforce_single_slide_deck
from backend.services.ppt_assistant.bullets import bullet_parts
from backend.services.ppt_assistant.json_extract import parse_llm_json_object
from backend.services.ppt_assistant import prompts
from backend.services.ppt_assistant.schema_validate import (
    coerce_ppt_elements,
    coerce_deck_plan,
    coerce_slide_deck,
    coerce_slide_object,
    validate_deck_plan,
    validate_ppt_elements,
    validate_slide_deck,
    validate_slide_object,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

PRESERVE_SLIDE_META_KEYS = frozenset({"locks", "sources", "extra"})


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


async def _coerce_validate_repair_loop(
    llm_chat: Callable[..., Any],
    *,
    initial: Dict[str, Any],
    coerce_fn: Callable[[Any], Dict[str, Any]],
    validate_fn: Callable[[Dict[str, Any]], List[str]],
    repair_kind: str,
    audit_base: str,
    max_repair_attempts: int,
) -> Dict[str, Any]:
    data = coerce_fn(initial)
    errors = validate_fn(data)
    n = 0
    while errors:
        if n >= max(0, max_repair_attempts):
            raise ValueError(
                "schema validation failed"
                + (f": {'; '.join(errors)}" if errors else "")
            )
        n += 1
        repair_user = prompts.repair_user_json(repair_kind, errors, data)
        fixed = await _llm_chat_json(
            llm_chat,
            system_prompt=prompts.REPAIR_JSON_SYSTEM,
            user_prompt=repair_user,
            audit_source=f"{audit_base}_repair",
        )
        data = coerce_fn(fixed)
        errors = validate_fn(data)
    return data


async def _llm_chat_json_validated(
    llm_chat: Callable[..., Any],
    *,
    system_prompt: str,
    user_prompt: str,
    audit_source: str,
    coerce_fn: Callable[[Any], Dict[str, Any]],
    validate_fn: Callable[[Dict[str, Any]], List[str]],
    repair_kind: str,
    max_repair_attempts: int = 2,
) -> Dict[str, Any]:
    first = await _llm_chat_json(
        llm_chat,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        audit_source=audit_source,
    )
    return await _coerce_validate_repair_loop(
        llm_chat,
        initial=first,
        coerce_fn=coerce_fn,
        validate_fn=validate_fn,
        repair_kind=repair_kind,
        audit_base=audit_source,
        max_repair_attempts=max_repair_attempts,
    )


def _ensure_version(data: Dict[str, Any]) -> None:
    if int(data.get("version", 1)) != 1:
        logger.warning("ppt_assistant: unexpected version %s", data.get("version"))


async def extract_ppt_elements(
    article: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    llm: Any,
    chunk_chars: int = 10_000,
    overlap: int = 400,
    max_repair_attempts: int = 2,
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
        data = await _llm_chat_json_validated(
            chat,
            system_prompt=prompts.EXTRACT_SYSTEM,
            user_prompt=user,
            audit_source="ppt_assistant_extract",
            coerce_fn=coerce_ppt_elements,
            validate_fn=validate_ppt_elements,
            repair_kind="ppt_elements",
            max_repair_attempts=max_repair_attempts,
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
    merged = await _llm_chat_json_validated(
        chat,
        system_prompt=prompts.MERGE_SYSTEM,
        user_prompt=user_merge,
        audit_source="ppt_assistant_merge",
        coerce_fn=coerce_ppt_elements,
        validate_fn=validate_ppt_elements,
        repair_kind="ppt_elements",
        max_repair_attempts=max_repair_attempts,
    )
    _ensure_version(merged)
    return merged


async def generate_slide_deck(
    ppt_elements: Dict[str, Any],
    *,
    constraints: Optional[str] = None,
    llm: Any,
    single_slide: bool = True,
    user_requirements: Optional[str] = None,
    generation_mode: str = "sequential",
    parallelism: int = 4,
    on_slide_ready: Optional[Callable[[int, Dict[str, Any]], Any]] = None,
    on_slide_failed: Optional[Callable[[int, str], Any]] = None,
    page_inputs: Optional[List[Dict[str, Any]]] = None,
    max_repair_attempts: int = 2,
) -> Dict[str, Any]:
    """ppt_elements → slide_deck。默认 **单张幻灯片**（一张上展示关键元素）。"""
    async def chat(**kw):
        return await llm.chat(**kw)

    blob = json.dumps(ppt_elements, ensure_ascii=False, indent=2)
    generation_mode = (generation_mode or "sequential").strip().lower()
    constraints_s = constraints or ""
    ur_s = user_requirements or ""

    if (not single_slide) and generation_mode == "parallel":
        # MVP：并行“页级内容生成”先限定为 kind=content 的 slides。
        async def plan_deck() -> Dict[str, Any]:
            plan_blob = prompts.plan_user(
                blob,
                constraints_s,
                user_requirements=ur_s,
            )
            return await _llm_chat_json_validated(
                chat,
                system_prompt=prompts.PLAN_SYSTEM,
                user_prompt=plan_blob,
                audit_source="ppt_assistant_deck_plan",
                coerce_fn=coerce_deck_plan,
                validate_fn=validate_deck_plan,
                repair_kind="deck_plan",
                max_repair_attempts=max_repair_attempts,
            )

        deck_plan = await plan_deck()
        slides_plan = deck_plan.get("slides") or []
        page_inputs_map: Dict[int, Dict[str, Any]] = {}
        if isinstance(page_inputs, list):
            for pi in page_inputs:
                if not isinstance(pi, dict):
                    continue
                if "index" not in pi:
                    continue
                try:
                    idx = int(pi["index"])
                except Exception:
                    continue
                page_inputs_map[idx] = pi
        sem = asyncio.Semaphore(max(1, int(parallelism)))

        async def draft_one(slide_plan: Dict[str, Any]) -> Dict[str, Any]:
            async with sem:
                idx = int(slide_plan.get("index", 1))
                pi = page_inputs_map.get(idx)
                # 如果用户提供了该页 page_input，则覆盖骨架标题/要点与 sources
                if pi:
                    if isinstance(pi.get("title_hint"), str) and pi.get("title_hint").strip():
                        slide_plan["title"] = pi["title_hint"].strip()
                    bh = pi.get("bullets_hint")
                    if isinstance(bh, list) and all(isinstance(x, str) for x in bh):
                        slide_plan["bullets"] = [x.strip() for x in bh if x.strip()]
                    srcs = pi.get("sources")
                    if isinstance(srcs, list) and all(isinstance(x, str) for x in srcs):
                        slide_plan["sources"] = [x for x in srcs]
                expected_texts = [
                    str(x).strip() for x in (slide_plan.get("bullets") or []) if str(x).strip()
                ]
                expected_sources = slide_plan.get("sources") or []
                if not isinstance(expected_sources, list):
                    expected_sources = []
                lu = prompts.page_draft_user(
                    blob,
                    slide_plan,
                    constraints_s,
                    user_requirements=ur_s,
                    page_input=pi or None,
                )

                def validate_fn(d: Dict[str, Any]) -> List[str]:
                    errs = validate_slide_object(d)
                    if int(d.get("index", 1)) != idx:
                        errs.append(f"slide.index 与计划不一致：expected={idx}")
                    actual_texts: List[str] = []
                    for b in (d.get("bullets") or []) or []:
                        t, _e = bullet_parts(b)
                        if t:
                            actual_texts.append(t)
                    missing = [t for t in expected_texts if t not in actual_texts]
                    if missing:
                        errs.append(
                            "bullets text 未能匹配计划（前几个缺失）：" + ",".join(missing[:5])
                        )
                    if expected_sources:
                        actual_sources = d.get("sources") or []
                        if set(actual_sources) != set(expected_sources):
                            errs.append(
                                "sources 未能匹配页级输入：" + ",".join(expected_sources)
                            )
                    return errs

                try:
                    slide = await _llm_chat_json_validated(
                        chat,
                        system_prompt=prompts.PAGE_DRAFT_SYSTEM,
                        user_prompt=lu,
                        audit_source=f"ppt_assistant_deck_page_{idx}",
                        coerce_fn=coerce_slide_object,
                        validate_fn=validate_fn,
                        repair_kind="slide_page",
                        max_repair_attempts=max_repair_attempts,
                    )
                    if on_slide_ready:
                        try:
                            on_slide_ready(idx, slide)
                        except Exception:
                            logger.exception("on_slide_ready callback failed")
                    return slide
                except Exception as e:
                    err = str(e)
                    if on_slide_failed:
                        try:
                            on_slide_failed(idx, err)
                        except Exception:
                            logger.exception("on_slide_failed callback failed")
                    # 占位页：保证 deck 合并时 schema 仍可过校验
                    expected_sources = slide_plan.get("sources") or []
                    if not isinstance(expected_sources, list):
                        expected_sources = []
                    return {
                        "index": idx,
                        "kind": "content",
                        "title": "生成失败（占位）",
                        "bullets": [],
                        "speaker_notes": "",
                        "sources": expected_sources,
                    }

        # 并行 Draft：每页独立 repair
        draft_tasks = [draft_one(s) for s in slides_plan if isinstance(s, dict)]
        drafted = await asyncio.gather(*draft_tasks)
        # 按 index 排序组装
        drafted_sorted = sorted(drafted, key=lambda s: int(s.get("index", 1)))
        deck = {"version": 1, "deck_title": deck_plan.get("deck_title") or "", "slides": drafted_sorted}
        errs = validate_slide_deck(deck, single_slide_final=False)
        if errs:
            raise ValueError("parallel deck validation failed: " + "; ".join(errs))
    else:
        system = (
            prompts.DECK_SYSTEM_SINGLE if single_slide else prompts.DECK_SYSTEM_MULTI
        )
        user = prompts.deck_user(
            blob,
            constraints_s,
            single_slide=single_slide,
            user_requirements=ur_s,
        )
        deck = await _llm_chat_json_validated(
            chat,
            system_prompt=system,
            user_prompt=user,
            audit_source="ppt_assistant_deck",
            coerce_fn=coerce_slide_deck,
            validate_fn=lambda d: validate_slide_deck(
                d, single_slide_final=False
            ),
            repair_kind="slide_deck",
            max_repair_attempts=max_repair_attempts,
        )

    if int(deck.get("version", 1)) != 1:
        logger.warning("slide_deck unexpected version %s", deck.get("version"))
    if single_slide:
        deck = enforce_single_slide_deck(deck)
        deck = await _coerce_validate_repair_loop(
            chat,
            initial=deck,
            coerce_fn=coerce_slide_deck,
            validate_fn=lambda d: validate_slide_deck(
                d, single_slide_final=True
            ),
            repair_kind="slide_deck",
            audit_base="ppt_assistant_deck_post_single",
            max_repair_attempts=max_repair_attempts,
        )
    return deck


def _slide_index_to_pos(slides: List[Any]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for i, s in enumerate(slides):
        if isinstance(s, dict) and isinstance(s.get("index"), int):
            out[int(s["index"])] = i
    return out


def _merge_refined_slide(
    old: Dict[str, Any],
    new: Dict[str, Any],
    *,
    locked: set[str],
) -> Dict[str, Any]:
    out = coerce_slide_object(new)
    out["index"] = int(old["index"])
    if "kind" in locked:
        out["kind"] = str(old.get("kind") or "content")
    else:
        out["kind"] = str(new.get("kind") or old.get("kind") or "content")
    for k in PRESERVE_SLIDE_META_KEYS:
        if k in old:
            out[k] = copy.deepcopy(old[k])
    for k in locked:
        if k in old:
            out[k] = copy.deepcopy(old[k])
    return out


async def _llm_chat_slide_validated(
    llm_chat: Callable[..., Any],
    *,
    system_prompt: str,
    user_prompt: str,
    audit_source: str,
    max_repair_attempts: int,
) -> Dict[str, Any]:
    return await _llm_chat_json_validated(
        llm_chat,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        audit_source=audit_source,
        coerce_fn=coerce_slide_object,
        validate_fn=validate_slide_object,
        repair_kind="slide_page",
        max_repair_attempts=max_repair_attempts,
    )


async def refine_slide_deck(
    slide_deck: Dict[str, Any],
    *,
    target_slide_indexes: List[int],
    instructions: str,
    llm: Any,
    ppt_elements: Optional[Dict[str, Any]] = None,
    locks: Optional[Dict[int, List[str]]] = None,
    user_requirements: Optional[str] = None,
    max_repair_attempts: int = 2,
) -> Dict[str, Any]:
    """
    按页局部重生成 slide_deck：未列入 target 的页保持不变。
    locks：slide_index -> 要保留的字段名列表（如 title、bullets、speaker_notes、kind）。
    locks/sources/extra 默认从旧页保留（与 design 一致）。
    """
    inst = (instructions or "").strip()
    if not inst:
        raise ValueError("instructions 不能为空")
    if not target_slide_indexes:
        raise ValueError("target_slide_indexes 不能为空")

    async def chat(**kw):
        return await llm.chat(**kw)

    deck = copy.deepcopy(coerce_slide_deck(slide_deck))
    slides = deck.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("slide_deck.slides 无效")

    pos_by_idx = _slide_index_to_pos(slides)
    lock_map = locks or {}
    pe_json = ""
    if ppt_elements is not None:
        pe_json = json.dumps(ppt_elements, ensure_ascii=False, indent=2)
    ur = (user_requirements or "").strip() or None

    for idx in sorted(set(int(i) for i in target_slide_indexes)):
        if idx not in pos_by_idx:
            raise ValueError(f"未找到 index={idx} 的幻灯片")
        p = pos_by_idx[idx]
        old = slides[p]
        if not isinstance(old, dict):
            raise ValueError(f"slides[{p}] 不是对象")
        lu = prompts.refine_slide_user(
            old,
            inst,
            ppt_elements_json=pe_json,
            user_requirements=ur or "",
        )
        new_slide = await _llm_chat_slide_validated(
            chat,
            system_prompt=prompts.REFINE_SLIDE_SYSTEM,
            user_prompt=lu,
            audit_source="ppt_assistant_refine_slide",
            max_repair_attempts=max_repair_attempts,
        )
        locked_names = set(lock_map.get(idx) or [])
        merged = _merge_refined_slide(old, new_slide, locked=locked_names)
        slides[p] = merged

    deck["slides"] = slides
    errs = validate_slide_deck(deck, single_slide_final=False)
    if errs:
        raise ValueError(f"refine 后 slide_deck 校验失败: {'; '.join(errs)}")
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
    generation_mode: str = "sequential",
    parallelism: int = 4,
    page_inputs: Optional[List[Dict[str, Any]]] = None,
    max_repair_attempts: int = 2,
) -> Dict[str, Any]:
    """extract → deck 一步完成（与 UI「运行」一致）。默认单页 deck。"""
    elements = await extract_ppt_elements(
        article,
        meta=meta,
        llm=llm,
        chunk_chars=chunk_chars,
        overlap=overlap,
        max_repair_attempts=max_repair_attempts,
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
        generation_mode=generation_mode,
        parallelism=parallelism,
        page_inputs=page_inputs,
        max_repair_attempts=max_repair_attempts,
    )
    return {"ppt_elements": elements, "slide_deck": deck}
