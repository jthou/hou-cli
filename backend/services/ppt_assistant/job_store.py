"""轻量 job store：为 ppt-assistant 的 run-stream 提供 run_id 可恢复能力。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import uuid4


RUN_TTL_SECONDS = 60 * 60  # 1 小时（MVP）


@dataclass
class SlideJobState:
    status: str = "pending"  # pending|ok|failed|cancelled
    slide: Optional[Dict[str, Any]] = None
    error: str = ""


@dataclass
class JobRecord:
    run_id: str
    created_at: float = field(default_factory=lambda: time.time())
    status: str = "running"  # running|done|failed|cancelled
    stage: str = "extract"  # extract|deck|done|error|cancelled
    ppt_elements: Optional[Dict[str, Any]] = None
    slide_deck: Optional[Dict[str, Any]] = None
    slide_deck_markdown: str = ""
    slides: Dict[int, SlideJobState] = field(default_factory=dict)
    error: str = ""


_JOBS: Dict[str, JobRecord] = {}


def new_run_id() -> str:
    return uuid4().hex


def _purge_expired(now: Optional[float] = None) -> None:
    t = now or time.time()
    expired = [
        rid for rid, rec in _JOBS.items() if (t - rec.created_at) > RUN_TTL_SECONDS
    ]
    for rid in expired:
        _JOBS.pop(rid, None)


def start_job(run_id: Optional[str] = None) -> JobRecord:
    _purge_expired()
    rid = run_id or new_run_id()
    rec = JobRecord(run_id=rid)
    _JOBS[rid] = rec
    return rec


def get_job(run_id: str) -> Optional[JobRecord]:
    _purge_expired()
    return _JOBS.get(run_id)


def set_extract_done(run_id: str, ppt_elements: Dict[str, Any]) -> None:
    rec = get_job(run_id)
    if not rec:
        return
    rec.ppt_elements = ppt_elements
    rec.stage = "deck"


def set_slide_ready(run_id: str, page_index: int, slide: Dict[str, Any]) -> None:
    rec = get_job(run_id)
    if not rec:
        return
    st = rec.slides.setdefault(page_index, SlideJobState())
    st.status = "ok"
    st.slide = slide
    st.error = ""


def set_slide_failed(run_id: str, page_index: int, error: str) -> None:
    rec = get_job(run_id)
    if not rec:
        return
    st = rec.slides.setdefault(page_index, SlideJobState())
    st.status = "failed"
    st.error = error or ""
    st.slide = None


def set_done(
    run_id: str,
    *,
    slide_deck: Dict[str, Any],
    slide_deck_markdown: str,
) -> None:
    rec = get_job(run_id)
    if not rec:
        return
    rec.status = "done"
    rec.stage = "done"
    rec.slide_deck = slide_deck
    rec.slide_deck_markdown = slide_deck_markdown or ""


def set_failed(run_id: str, error: str) -> None:
    rec = get_job(run_id)
    if not rec:
        return
    rec.status = "failed"
    rec.stage = "error"
    rec.error = error or ""


def set_cancelled(run_id: str) -> None:
    rec = get_job(run_id)
    if not rec:
        return
    rec.status = "cancelled"
    rec.stage = "cancelled"


def job_to_public_dict(rec: JobRecord) -> Dict[str, Any]:
    slides_summary: Dict[str, Any] = {}
    for idx, st in rec.slides.items():
        slides_summary[str(idx)] = {
            "status": st.status,
            "error": st.error,
        }
    return {
        "run_id": rec.run_id,
        "status": rec.status,
        "stage": rec.stage,
        "ppt_elements": rec.ppt_elements,
        "slide_deck": rec.slide_deck,
        "slide_deck_markdown": rec.slide_deck_markdown,
        "slides": slides_summary,
        "error": rec.error,
    }

