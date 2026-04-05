"""ppt_elements / slide_deck：coerce 与校验（无 LLM，可单测）。"""

from __future__ import annotations

from typing import Any, Dict, List


def coerce_ppt_elements(data: Any) -> Dict[str, Any]:
    """补全缺省字段，version 规范为 1。"""
    if not isinstance(data, dict):
        data = {}
    out: Dict[str, Any] = dict(data)
    out["version"] = 1
    meta = out.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("source_hint", "")
    meta.setdefault("audience", "")
    meta.setdefault("constraints_note", "")
    meta.setdefault("user_requirements", "")
    out["meta"] = meta
    for k in (
        "one_liner",
        "takeaway",
    ):
        out[k] = str(out.get(k) or "")
    for k in (
        "outline_sections",
        "highlight_numbers",
        "terms",
        "layout_hints",
    ):
        v = out.get(k)
        out[k] = v if isinstance(v, list) else []
    return out


def validate_ppt_elements(data: Dict[str, Any]) -> List[str]:
    """返回人类可读错误列表；空表示通过。"""
    errs: List[str] = []
    if not isinstance(data, dict):
        return ["根对象必须是 JSON 对象"]
    if int(data.get("version", 1) or 1) != 1:
        errs.append("version 必须为 1")
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errs.append("meta 必须是对象")
    for k in ("one_liner", "takeaway"):
        if k in data and not isinstance(data.get(k), str):
            errs.append(f"{k} 必须是字符串")
    sections = data.get("outline_sections")
    if not isinstance(sections, list):
        errs.append("outline_sections 必须是数组")
    else:
        for i, sec in enumerate(sections):
            if not isinstance(sec, dict):
                errs.append(f"outline_sections[{i}] 必须是对象")
                continue
            for req in ("id", "title"):
                if req not in sec or not str(sec.get(req) or "").strip():
                    errs.append(f"outline_sections[{i}] 缺少 {req}")
            kc = sec.get("key_claims")
            if kc is None:
                errs.append(f"outline_sections[{i}] 缺少 key_claims")
            elif not isinstance(kc, list):
                errs.append(f"outline_sections[{i}].key_claims 必须是数组")
            else:
                for j, cl in enumerate(kc):
                    if not isinstance(cl, dict):
                        errs.append(f"outline_sections[{i}].key_claims[{j}] 必须是对象")
                        continue
                    if not str(cl.get("claim") or "").strip():
                        errs.append(
                            f"outline_sections[{i}].key_claims[{j}].claim 不能为空"
                        )
                    for arr_name in ("bullets", "evidence_quotes"):
                        a = cl.get(arr_name)
                        if a is not None and not isinstance(a, list):
                            errs.append(
                                f"outline_sections[{i}].key_claims[{j}].{arr_name} 必须是数组"
                            )
                    se = cl.get("speaker_elaboration")
                    if se is not None and not isinstance(se, str):
                        errs.append(
                            f"outline_sections[{i}].key_claims[{j}].speaker_elaboration 必须是字符串"
                        )
    for name in ("highlight_numbers", "terms", "layout_hints"):
        v = data.get(name)
        if v is not None and not isinstance(v, list):
            errs.append(f"{name} 必须是数组")
    return errs


def coerce_slide_deck(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    out: Dict[str, Any] = dict(data)
    out["version"] = 1
    out["deck_title"] = str(out.get("deck_title") or "")
    slides = out.get("slides")
    out["slides"] = slides if isinstance(slides, list) else []
    return out


def validate_slide_deck(
    data: Dict[str, Any],
    *,
    single_slide_final: bool = False,
) -> List[str]:
    """
    校验 slide_deck。
    single_slide_final=True 时要求 slides 长度恰好为 1（用于单页模式 normalize 之后）。
    """
    errs: List[str] = []
    if not isinstance(data, dict):
        return ["根对象必须是 JSON 对象"]
    if int(data.get("version", 1) or 1) != 1:
        errs.append("version 必须为 1")
    if "deck_title" not in data:
        errs.append("缺少 deck_title")
    elif not isinstance(data.get("deck_title"), str):
        errs.append("deck_title 必须是字符串")
    slides = data.get("slides")
    if not isinstance(slides, list):
        errs.append("slides 必须是数组")
        return errs
    if len(slides) == 0:
        errs.append("slides 不能为空")
    if single_slide_final and len(slides) != 1:
        errs.append(f"单页模式下 slides 必须恰好 1 页，当前 {len(slides)}")
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            errs.append(f"slides[{i}] 必须是对象")
            continue
        if not isinstance(s.get("index"), int):
            errs.append(f"slides[{i}].index 必须是整数")
        kind = s.get("kind")
        if kind is not None and not isinstance(kind, str):
            errs.append(f"slides[{i}].kind 必须是字符串")
        if "title" not in s or not isinstance(s.get("title"), str):
            errs.append(f"slides[{i}].title 必须是字符串")
        bul = s.get("bullets")
        if bul is None:
            errs.append(f"slides[{i}] 缺少 bullets")
        elif not isinstance(bul, list):
            errs.append(f"slides[{i}].bullets 必须是数组")
        sn = s.get("speaker_notes")
        if sn is not None and not isinstance(sn, str):
            errs.append(f"slides[{i}].speaker_notes 必须是字符串")
        for opt in ("subtitle", "lead", "body_summary", "body_text", "text_scheme"):
            v = s.get(opt)
            if v is not None and not isinstance(v, str):
                errs.append(f"slides[{i}].{opt} 必须是字符串")
    return errs


def coerce_slide_object(data: Any) -> Dict[str, Any]:
    """单页 JSON 补全类型（用于 refine）。"""
    if not isinstance(data, dict):
        data = {}
    out: Dict[str, Any] = dict(data)
    idx = out.get("index")
    if isinstance(idx, int):
        pass
    elif isinstance(idx, float) and idx == int(idx):
        out["index"] = int(idx)
    elif isinstance(idx, str) and idx.strip().isdigit():
        out["index"] = int(idx.strip())
    else:
        out["index"] = 1
    out["kind"] = str(out.get("kind") or "content").strip() or "content"
    out["title"] = str(out.get("title") or "")
    out["speaker_notes"] = str(out.get("speaker_notes") or "")
    out["subtitle"] = str(out.get("subtitle") or "")
    out["lead"] = str(out.get("lead") or "")
    out["body_summary"] = str(out.get("body_summary") or "")
    out["body_text"] = str(out.get("body_text") or "")
    out["text_scheme"] = str(out.get("text_scheme") or "").strip()
    bul = out.get("bullets")
    out["bullets"] = bul if isinstance(bul, list) else []
    src = out.get("sources")
    out["sources"] = src if isinstance(src, list) else []
    # extra/locks 为可选透传；不在 schema 强制
    extra = out.get("extra")
    out["extra"] = extra if isinstance(extra, dict) else (out.get("extra") if isinstance(out.get("extra"), dict) else {})
    locks = out.get("locks")
    out["locks"] = locks if isinstance(locks, dict) else {}
    return out


def validate_slide_object(slide: Any) -> List[str]:
    """校验单页对象（用于 refine 输出）。"""
    if not isinstance(slide, dict):
        return ["幻灯片必须是 JSON 对象"]
    errs: List[str] = []
    if not isinstance(slide.get("index"), int):
        errs.append("index 必须是整数")
    kind = slide.get("kind")
    if kind is not None and not isinstance(kind, str):
        errs.append("kind 必须是字符串")
    if "title" not in slide or not isinstance(slide.get("title"), str):
        errs.append("title 必须是字符串")
    bul = slide.get("bullets")
    if bul is None:
        errs.append("缺少 bullets")
    elif not isinstance(bul, list):
        errs.append("bullets 必须是数组")
    sn = slide.get("speaker_notes")
    if sn is not None and not isinstance(sn, str):
        errs.append("speaker_notes 必须是字符串")
    src = slide.get("sources")
    if src is not None and not isinstance(src, list):
        errs.append("sources 必须是数组")
    elif isinstance(src, list):
        for i, x in enumerate(src):
            if not isinstance(x, str):
                errs.append(f"sources[{i}] 必须是字符串")
    for opt in ("subtitle", "lead", "body_summary", "body_text", "text_scheme"):
        v = slide.get(opt)
        if v is not None and not isinstance(v, str):
            errs.append(f"{opt} 必须是字符串")
    return errs


def coerce_deck_plan(data: Any) -> Dict[str, Any]:
    """deck_plan：用于并行生成多页的页级骨架（无 speaker_elaboration）。"""
    if not isinstance(data, dict):
        data = {}
    out: Dict[str, Any] = dict(data)
    out["version"] = 1
    out["deck_title"] = str(out.get("deck_title") or "")
    slides = out.get("slides")
    out["slides"] = slides if isinstance(slides, list) else []
    for i, s in enumerate(out["slides"]):
        if not isinstance(s, dict):
            out["slides"][i] = {}
    return out


def validate_deck_plan(data: Dict[str, Any]) -> List[str]:
    """校验 deck_plan；失败则进入 repair。"""
    errs: List[str] = []
    if not isinstance(data, dict):
        return ["deck_plan 必须是 JSON 对象"]
    if int(data.get("version", 1) or 1) != 1:
        errs.append("deck_plan.version 必须为 1")
    if not isinstance(data.get("deck_title"), str):
        errs.append("deck_plan.deck_title 必须是字符串")
    slides = data.get("slides")
    if not isinstance(slides, list):
        errs.append("deck_plan.slides 必须是数组")
        return errs
    if len(slides) == 0:
        errs.append("deck_plan.slides 不能为空")
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            errs.append(f"deck_plan.slides[{i}] 必须是对象")
            continue
        idx = s.get("index")
        if not isinstance(idx, int):
            errs.append(f"deck_plan.slides[{i}].index 必须是整数")
        title = s.get("title")
        if not isinstance(title, str):
            errs.append(f"deck_plan.slides[{i}].title 必须是字符串")
        bullets = s.get("bullets")
        if bullets is None or not isinstance(bullets, list):
            errs.append(f"deck_plan.slides[{i}].bullets 必须是数组")
        else:
            for j, b in enumerate(bullets):
                if not isinstance(b, str):
                    errs.append(
                        f"deck_plan.slides[{i}].bullets[{j}] 必须是字符串"
                    )
        kind = s.get("kind")
        # MVP：并行 draft 先只处理 content 页，transition/title 先不进入 plan。
        if kind is not None and kind != "content":
            errs.append(f"deck_plan.slides[{i}].kind 仅允许 content（当前={kind!r}）")
    return errs
