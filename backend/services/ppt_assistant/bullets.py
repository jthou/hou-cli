"""slide_deck bullets：兼容字符串与 { text, speaker_elaboration } 对象。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def bullet_slide_hint(b: Any) -> str:
    """片上可见的一句短提示（标题下小字），与 speaker_elaboration（仅讲述区长文）区分。"""
    if b is None or not isinstance(b, dict):
        return ""
    return str(b.get("slide_hint") or b.get("hint") or b.get("short_prompt") or "").strip()


def bullet_parts(b: Any) -> Tuple[str, str]:
    """返回（片上短句, 讲者阐述）；阐述可为空。"""
    if b is None:
        return "", ""
    if isinstance(b, dict):
        t = str(b.get("text") or b.get("point") or b.get("slide") or "").strip()
        e = str(b.get("speaker_elaboration") or b.get("elaboration") or "").strip()
        return t, e
    return str(b).strip(), ""


def bullet_to_dict(b: Any) -> Optional[Dict[str, str]]:
    t, e = bullet_parts(b)
    if not t:
        return None
    h = bullet_slide_hint(b)
    out: Dict[str, str] = {"text": t, "speaker_elaboration": e}
    if h:
        out["slide_hint"] = h
    return out


def bullet_dicts_for_slide(bullets: Any) -> List[Dict[str, str]]:
    """将一页的 bullets 规范为字典列表（供合并或与 JSON 统一）。"""
    out: List[Dict[str, str]] = []
    if not isinstance(bullets, list):
        return out
    for b in bullets:
        d = bullet_to_dict(b)
        if d:
            out.append(d)
    return out
