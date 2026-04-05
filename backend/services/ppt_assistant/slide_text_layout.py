"""幻灯片正文排版：扩展 bullets 列表之外的几种可见文案形态（可选字段 + text_scheme）。"""

from __future__ import annotations

from typing import Any, Dict

from backend.services.ppt_assistant.bullets import bullet_parts

TEXT_SCHEME_BULLETS = "bullets"
TEXT_SCHEME_TITLE_ONLY = "title_only"
TEXT_SCHEME_LONG_PROSE = "long_prose"
TEXT_SCHEME_TITLE_LEAD = "title_lead"
TEXT_SCHEME_TITLE_SUBTITLE_LEAD = "title_subtitle_lead"

_KNOWN = frozenset(
    {
        TEXT_SCHEME_BULLETS,
        TEXT_SCHEME_TITLE_ONLY,
        TEXT_SCHEME_LONG_PROSE,
        TEXT_SCHEME_TITLE_LEAD,
        TEXT_SCHEME_TITLE_SUBTITLE_LEAD,
    }
)


def _norm_scheme(raw: str) -> str:
    x = (raw or "").strip().lower().replace("-", "_")
    aliases = {
        "classic": TEXT_SCHEME_BULLETS,
        "bullets_classic": TEXT_SCHEME_BULLETS,
        "title_short": TEXT_SCHEME_TITLE_LEAD,
        "title_subtitle_short": TEXT_SCHEME_TITLE_SUBTITLE_LEAD,
    }
    return aliases.get(x, x)


def slide_lead_text(slide: Dict[str, Any]) -> str:
    return str(slide.get("lead") or slide.get("body_summary") or "").strip()


def slide_subtitle_text(slide: Dict[str, Any]) -> str:
    return str(slide.get("subtitle") or "").strip()


def slide_body_long_text(slide: Dict[str, Any]) -> str:
    """长说明正文：优先 body_text，否则用首条要点的 text+阐述拼成一段。"""
    bt = str(slide.get("body_text") or "").strip()
    if bt:
        return bt
    bullets = slide.get("bullets") if isinstance(slide.get("bullets"), list) else []
    if len(bullets) != 1:
        return ""
    t, e = bullet_parts(bullets[0])
    parts = [p for p in (t, e) if p]
    return "\n\n".join(parts).strip()


def effective_text_scheme(slide: Dict[str, Any]) -> str:
    """
    解析本页正文方案。未显式写 text_scheme 时按字段推断（兼容旧 deck）。
    """
    if not isinstance(slide, dict):
        return TEXT_SCHEME_BULLETS
    raw = _norm_scheme(str(slide.get("text_scheme") or ""))
    if raw in _KNOWN:
        return raw
    subtitle = slide_subtitle_text(slide)
    lead = slide_lead_text(slide)
    body_long = slide_body_long_text(slide)
    bullets = slide.get("bullets") if isinstance(slide.get("bullets"), list) else []
    n_bullets = sum(1 for b in bullets if bullet_parts(b)[0])

    if subtitle and lead:
        return TEXT_SCHEME_TITLE_SUBTITLE_LEAD
    if lead and n_bullets == 0:
        return TEXT_SCHEME_TITLE_LEAD
    if body_long and n_bullets == 0:
        return TEXT_SCHEME_LONG_PROSE
    if n_bullets == 0 and not lead and not body_long and not subtitle:
        return TEXT_SCHEME_TITLE_ONLY
    return TEXT_SCHEME_BULLETS
