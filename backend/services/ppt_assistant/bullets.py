"""slide_deck bullets：兼容字符串与 { text, speaker_elaboration } 对象。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


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
    return {"text": t, "speaker_elaboration": e}


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
