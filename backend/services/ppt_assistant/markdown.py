"""slide_deck → Markdown（供预览与下载）。"""

from __future__ import annotations

from typing import Any, Dict

from backend.services.ppt_assistant.bullets import bullet_parts, bullet_slide_hint
from backend.services.ppt_assistant.slide_text_layout import (
    effective_text_scheme,
    slide_body_long_text,
    slide_lead_text,
    slide_subtitle_text,
    TEXT_SCHEME_LONG_PROSE,
    TEXT_SCHEME_TITLE_LEAD,
    TEXT_SCHEME_TITLE_ONLY,
    TEXT_SCHEME_TITLE_SUBTITLE_LEAD,
)


def slide_deck_to_markdown(deck: Dict[str, Any]) -> str:
    """将 slide_deck 结构转为可读 Markdown。"""
    title = (deck.get("deck_title") or "演示").strip()
    lines = [f"# {title}", ""]
    slides = deck.get("slides") or []
    if not isinstance(slides, list):
        return "\n".join(lines)

    for s in slides:
        if not isinstance(s, dict):
            continue
        idx = s.get("index", 0)
        kind = (s.get("kind") or "content").strip()
        stitle = (s.get("title") or "").strip()
        bullets = s.get("bullets") or []
        notes = (s.get("speaker_notes") or "").strip()

        lines.append(f"## 第 {idx} 页 ({kind}) — {stitle}".strip())
        lines.append("")
        scheme = effective_text_scheme(s) if isinstance(s, dict) else "bullets"
        if scheme == TEXT_SCHEME_TITLE_ONLY:
            lines.append("*（本页仅有标题，无正文要点）*")
            lines.append("")
        elif scheme == TEXT_SCHEME_TITLE_LEAD:
            lead = slide_lead_text(s) if isinstance(s, dict) else ""
            if lead:
                lines.append(lead)
                lines.append("")
        elif scheme == TEXT_SCHEME_TITLE_SUBTITLE_LEAD:
            sub = slide_subtitle_text(s) if isinstance(s, dict) else ""
            lead = slide_lead_text(s) if isinstance(s, dict) else ""
            if sub:
                lines.append(f"### {sub}")
                lines.append("")
            if lead:
                lines.append(lead)
                lines.append("")
        elif scheme == TEXT_SCHEME_LONG_PROSE:
            prose = slide_body_long_text(s) if isinstance(s, dict) else ""
            if prose:
                for para in prose.split("\n\n"):
                    lines.append(para.strip())
                    lines.append("")
        elif isinstance(bullets, list):
            for b in bullets:
                t, e = bullet_parts(b)
                if not t:
                    continue
                lines.append(f"- **{t}**")
                sh = bullet_slide_hint(b)
                if sh:
                    lines.append(f"  *〔片上短提示〕{sh}*")
                    lines.append("")
                if e:
                    lines.append("")
                    lines.append(f"  > {e}")
                    lines.append("")
                else:
                    lines.append("")
        if notes:
            lines.append(f"*本页备注：{notes}*")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
