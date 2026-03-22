"""首页简报 API：读取最新成功简报、触发生成任务。

时间：2026-03-21；理由：P0 设计落地；方法：读任务队列中 home_briefing_report 最新 completed + POST 创建任务。
更新时间：2026-03-21；P1：合并多状态列表，失败时仍返回上一期 briefing + show_degraded_banner。
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.infrastructure.storage.task_queue_db import TaskPriority, get_task_queue_db
from backend.infrastructure.execution.task_handlers import validate_task_creation
from backend.services.home_briefing.latest_payload import build_latest_home_briefing_payload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/home-briefing/latest")
async def get_latest_home_briefing():
    """
    返回最近一次**成功**简报；并附带最近一次尝试（可能失败/排队中）。
    - `show_degraded_banner`: 最近一次任务失败且时间上晚于上一期成功 → 前端展示「本期失败，以下为上一期」。
    - `pending_in_queue`: 最近一次任务仍在 queued/running。
    """
    db = get_task_queue_db()
    tasks = db.list_tasks(
        status=None,
        limit=40,
        offset=0,
        include_deleted="exclude",
        include_result=True,
        task_types=["home_briefing_report"],
    )
    return build_latest_home_briefing_payload(tasks)


class HomeBriefingGenerateRequest(BaseModel):
    window_hours: Optional[int] = None
    max_facts: Optional[int] = None
    model: Optional[str] = None


@router.post("/home-briefing/generate")
async def enqueue_home_briefing_generate(body: Optional[HomeBriefingGenerateRequest] = None):
    """入队一条 home_briefing_report 任务；由 Worker 异步执行。"""
    meta: Dict[str, Any] = {}
    if body:
        if body.window_hours is not None:
            meta["window_hours"] = body.window_hours
        if body.max_facts is not None:
            meta["max_facts"] = body.max_facts
        if body.model:
            meta["model"] = body.model.strip()
    ok, err = validate_task_creation("home_briefing_report", meta)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    db = get_task_queue_db()
    task_name = f"首页简报生成 {datetime.now().strftime('%m-%d %H:%M')}"
    task_id = db.create_task(
        task_type="home_briefing_report",
        task_name=task_name,
        priority=TaskPriority.NORMAL,
        metadata=meta,
    )
    return {"success": True, "task_id": task_id, "message": "已加入队列，完成后刷新首页即可查看最新简报"}
