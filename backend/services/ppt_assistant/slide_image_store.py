"""PPT 幻灯片配图任务：按 job_id 落盘并在导出时读取路径（内存 + 磁盘）。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from shared.platform_utils import get_task_output_dir

JOB_TTL_SECONDS = 60 * 60 * 2


@dataclass
class SlideImageJob:
    job_id: str
    base_dir: Path
    created_at: float = field(default_factory=lambda: time.time())
    images: Dict[int, str] = field(default_factory=dict)
    errors: Dict[int, str] = field(default_factory=dict)


_STORE: Dict[str, SlideImageJob] = {}


def _purge() -> None:
    now = time.time()
    for jid, rec in list(_STORE.items()):
        if now - rec.created_at > JOB_TTL_SECONDS:
            _STORE.pop(jid, None)


def create_slide_image_job() -> SlideImageJob:
    _purge()
    jid = uuid4().hex
    base = get_task_output_dir("ppt-slide-images") / jid
    base.mkdir(parents=True, exist_ok=True)
    rec = SlideImageJob(job_id=jid, base_dir=base.resolve())
    _STORE[jid] = rec
    return rec


def reuse_or_create_slide_image_job(job_id: Optional[str]) -> SlideImageJob:
    """
    若 job_id 仍有效则延长存活并复用目录（用于仅补跑失败页）；否则新建任务。
    """
    _purge()
    raw = (job_id or "").strip()
    if raw and raw in _STORE:
        rec = _STORE[raw]
        rec.created_at = time.time()
        return rec
    return create_slide_image_job()


def get_slide_image_job(job_id: str) -> Optional[SlideImageJob]:
    _purge()
    if not job_id or job_id not in _STORE:
        return None
    return _STORE[job_id]


def record_slide_image(job_id: str, page_index: int, abs_path: str) -> None:
    rec = get_slide_image_job(job_id)
    if rec:
        rec.images[int(page_index)] = abs_path
        rec.errors.pop(int(page_index), None)


def record_slide_image_error(job_id: str, page_index: int, err: str) -> None:
    rec = get_slide_image_job(job_id)
    if rec:
        rec.errors[int(page_index)] = err or "unknown"


def safe_image_file(job_id: str, page_index: int) -> Optional[Path]:
    """返回已生成图片的路径；若不存在或越界则 None。"""
    rec = get_slide_image_job(job_id)
    if not rec:
        return None
    p = Path(rec.images.get(int(page_index)) or "")
    if not p.is_file():
        return None
    try:
        rp = p.resolve()
        base = rec.base_dir.resolve()
        rp.relative_to(base)
    except ValueError:
        return None
    return rp


def job_images_for_export(job_id: str) -> Dict[int, str]:
    rec = get_slide_image_job(job_id)
    if not rec:
        return {}
    out: Dict[int, str] = {}
    for k, path in rec.images.items():
        pp = Path(path)
        if pp.is_file():
            out[int(k)] = str(pp.resolve())
    return out
