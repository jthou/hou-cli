"""slide_deck 后处理：单页模式下降多张合并为一张。"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.services.ppt_assistant.bullets import bullet_parts, bullet_to_dict


def enforce_single_slide_deck(deck: Dict[str, Any]) -> Dict[str, Any]:
    """
    将模型返回的多页 deck 规范为 **恰好一张 content 页**（index=1）。
    标题取 deck_title 或首个非空页标题；要点合并去重，上限 14 条；备注拼接截断。
    bullets 统一为 { text, speaker_elaboration }。
    """
    slides = deck.get("slides")
    if not isinstance(slides, list):
        return deck

    def _normalize_one_slide(s: Dict[str, Any]) -> Dict[str, Any]:
        norm: List[Dict[str, str]] = []
        for b in s.get("bullets") or []:
            d = bullet_to_dict(b)
            if d:
                norm.append(d)
        out = {**s, "index": 1, "kind": (s.get("kind") or "content"), "bullets": norm}
        return out

    if len(slides) <= 1:
        if slides and isinstance(slides[0], dict):
            slides[0] = _normalize_one_slide(slides[0])
        return deck

    deck_title = (deck.get("deck_title") or "").strip()
    ordered: List[Dict[str, str]] = []
    seen_text: set[str] = set()
    primary_title = ""

    for s in slides:
        if not isinstance(s, dict):
            continue
        kind = (s.get("kind") or "content").strip()
        if kind == "transition":
            continue
        st = (s.get("title") or "").strip()
        if st and not primary_title:
            primary_title = st
        for b in s.get("bullets") or []:
            t, e = bullet_parts(b)
            if not t:
                continue
            if t not in seen_text:
                seen_text.add(t)
                ordered.append({"text": t, "speaker_elaboration": e})
            elif e:
                for item in ordered:
                    if item["text"] == t:
                        old = item.get("speaker_elaboration") or ""
                        merged = (old + "\n\n" + e).strip() if old else e
                        item["speaker_elaboration"] = merged[:1200]
                        break

    ordered = ordered[:14]
    title = deck_title or primary_title or "要点"

    notes_parts: List[str] = []
    for s in slides:
        if isinstance(s, dict) and s.get("speaker_notes"):
            n = str(s["speaker_notes"]).strip()
            if n:
                notes_parts.append(n)
    notes = " ".join(notes_parts)[:800]

    deck["slides"] = [
        {
            "index": 1,
            "kind": "content",
            "title": title,
            "bullets": ordered,
            "speaker_notes": notes,
        }
    ]
    return deck
