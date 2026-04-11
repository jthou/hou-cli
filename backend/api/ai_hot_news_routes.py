# 时间：2026-04-04；理由：阅读页热点不入任务队列，需同编排直跑；方法：POST /api/ai-hot-news/run 调用 run_ai_hot_news_digest
"""今日 AI 热点：HTTP 同步执行（不入队）。"""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from backend.infrastructure.execution.task_handlers import validate_task_creation
from backend.services.ai_hot_news_digest.run_digest import run_ai_hot_news_digest

logger = logging.getLogger(__name__)

router = APIRouter()


class AiHotNewsRunRequest(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/ai-hot-news/run")
async def ai_hot_news_run(body: AiHotNewsRunRequest = Body(...)):
    """
    在当前请求内执行完整热点编排（多轮检索 + LLM），**不写入任务队列**。
    成功时 ``result`` 与任务完成态的 ``result`` 字段结构一致，便于前端复用 TaskResultDisplay。
    """
    meta: Dict[str, Any] = dict(body.metadata or {})
    ok, err = validate_task_creation("ai_hot_news_digest", meta)
    if not ok:
        raise HTTPException(status_code=400, detail=err or "metadata 校验失败")
    try:
        out = await run_ai_hot_news_digest(meta)
    except Exception as e:
        logger.exception("ai-hot-news/run failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    if out.get("status") != "success":
        raise HTTPException(status_code=500, detail=out.get("summary") or "生成失败")
    return {"success": True, "result": out}
