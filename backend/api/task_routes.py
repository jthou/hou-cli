"""任务管理 API 路由"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from backend.core.agent.task_manager import task_manager, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务状态"""
    task_info = task_manager.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return {
        "success": True,
        "task": task_info.to_dict()
    }


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 50):
    """列出任务"""
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的任务状态: {status}")
    
    tasks = task_manager.list_tasks(task_status)
    # 按创建时间倒序排列，取最新的
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    tasks = tasks[:limit]
    
    return {
        "success": True,
        "tasks": [task.to_dict() for task in tasks],
        "count": len(tasks)
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    success = await task_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在或无法取消: {task_id}")
    
    return {
        "success": True,
        "message": f"任务 {task_id} 已取消"
    }

