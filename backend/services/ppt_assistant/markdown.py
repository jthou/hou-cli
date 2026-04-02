"""slide_deck → Markdown（供预览与下载）。"""

from __future__ import annotations

from typing import Any, Dict

from backend.services.ppt_assistant.bullets import bullet_parts


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
        if isinstance(bullets, list):
            for b in bullets:
                t, e = bullet_parts(b)
                if not t:
                    continue
                lines.append(f"- **{t}**")
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
