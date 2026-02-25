"""任务队列 API 路由"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from backend.infrastructure.storage.task_queue_db import (
    get_task_queue_db,
    TaskStatus,
    TaskPriority
)
from backend.infrastructure.execution.task_handlers import validate_task_creation
from shared.debug_utils import debug_log

logger = logging.getLogger(__name__)

router = APIRouter()


from pydantic import BaseModel

class TaskCreateRequest(BaseModel):
    task_type: str
    task_name: Optional[str] = None  # 留空则根据类型和参数自动生成
    priority: Optional[int] = None
    max_retries: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


def _generate_task_name(task_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """根据任务类型和参数自动生成任务名称"""
    from datetime import datetime
    ts = datetime.now().strftime("%m-%d %H:%M")
    meta = metadata or {}

    if task_type == "weather_query":
        loc = meta.get("location", "")
        qt = meta.get("query_type", "current")
        if loc:
            return f"{loc}{'天气预报' if qt == 'forecast' else '天气查询'} {ts}"
        return f"天气查询 {ts}"

    if task_type == "video_download":
        u = meta.get("url", "")
        short = u[:40] + "..." if len(u) > 40 else u
        return f"视频下载 {short} {ts}"

    if task_type == "speech_to_text":
        inp = meta.get("input_file", "")
        short = (Path(inp).name[:30] + "..." if len(Path(inp).name) > 30 else Path(inp).name) if inp else "语音"
        return f"语音转文字 {short} {ts}"

    if task_type == "video_extract_audio":
        inp = meta.get("input_file", "")
        short = (Path(inp).name[:30] + "..." if len(Path(inp).name) > 30 else Path(inp).name) if inp else "视频"
        return f"视频提音频 {short} {ts}"

    type_names = {
        "weather_query": "天气查询",
        "video_download": "视频下载",
        "speech_to_text": "语音转文字",
        "video_extract_audio": "视频提取音频",
    }
    name = type_names.get(task_type, task_type)
    return f"{name} {ts}"


class ScheduledTaskCreateRequest(BaseModel):
    task_type: str
    task_name: str
    schedule_type: str  # 'interval' 或 'cron'
    schedule_config: Dict[str, Any]  # {"interval_seconds": 3600} 或 cron 表达式
    metadata: Optional[Dict[str, Any]] = None


@router.get("/task-queue/debug")
async def task_queue_debug():
    """诊断接口：确认 task-queue API 已挂载"""
    return {"ok": True, "message": "task-queue API available"}


@router.post("/task-queue/tasks")
async def create_task(request: TaskCreateRequest):
    """
    创建新任务
    
    Args:
        task_type: 任务类型
        task_name: 任务名称
        priority: 任务优先级（1-4，默认 2）
        max_retries: 最大重试次数（默认 3）
        metadata: 任务元数据
    """
    try:
        task_queue_db = get_task_queue_db()
        
        # 验证任务类型与 metadata（通用任务管理验证规范）
        ok, err = validate_task_creation(request.task_type, request.metadata)
        if not ok:
            raise HTTPException(status_code=400, detail=err)

        # 验证优先级
        if request.priority is None:
            priority = TaskPriority.NORMAL
        else:
            try:
                priority = TaskPriority(request.priority)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的优先级: {request.priority}，必须是 1-4"
                )

        # 任务名称：留空则自动生成
        task_name = (request.task_name or "").strip()
        if not task_name:
            task_name = _generate_task_name(request.task_type, request.metadata)
        
        # 创建任务（创建即入队，由 Worker 轮询拉取）
        task_id = task_queue_db.create_task(
            task_type=request.task_type,
            task_name=task_name,
            priority=priority,
            max_retries=request.max_retries or 3,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已创建"
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"创建任务失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"创建任务失败: {str(e)}"
        )


@router.get("/task-queue/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务信息"""
    try:
        task_queue_db = get_task_queue_db()
        task = task_queue_db.get_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"任务不存在: {task_id}"
            )
        
        return {
            "success": True,
            "task": task
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"获取任务失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"获取任务失败: {str(e)}"
        )


@router.get("/task-queue/tasks")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """列出任务"""
    try:
        task_queue_db = get_task_queue_db()
        
        # 解析状态
        task_status = None
        if status:
            try:
                task_status = TaskStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的任务状态: {status}"
                )
        
        tasks = task_queue_db.list_tasks(
            status=task_status,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"列出任务失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"列出任务失败: {str(e)}"
        )


@router.post("/task-queue/tasks/{task_id}/restart")
async def restart_task(task_id: str):
    """基于原任务重新开始：按原 task_type、metadata、priority 创建一条新任务并入队"""
    try:
        task_queue_db = get_task_queue_db()
        task = task_queue_db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        task_type = task.get("task_type")
        metadata = task.get("metadata") or {}
        priority = task.get("priority")
        if priority is None:
            priority = TaskPriority.NORMAL
        else:
            try:
                priority = TaskPriority(priority)
            except ValueError:
                priority = TaskPriority.NORMAL

        ok, err = validate_task_creation(task_type, metadata)
        if not ok:
            raise HTTPException(status_code=400, detail=err)

        task_name = _generate_task_name(task_type, metadata)
        new_task_id = task_queue_db.create_task(
            task_type=task_type,
            task_name=task_name,
            priority=priority,
            max_retries=3,
            metadata=metadata,
        )

        return {
            "success": True,
            "task_id": new_task_id,
            "message": "已基于原任务创建新任务",
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"重新开始任务失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"重新开始失败: {str(e)}")


@router.post("/task-queue/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        task_queue_db = get_task_queue_db()
        success = task_queue_db.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"任务不存在或无法取消: {task_id}"
            )
        
        return {
            "success": True,
            "message": f"任务 {task_id} 已取消"
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"取消任务失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"取消任务失败: {str(e)}"
        )


@router.get("/task-queue/workers")
async def list_workers():
    """列出所有 Worker"""
    try:
        task_queue_db = get_task_queue_db()
        workers = task_queue_db.list_workers()
        
        return {
            "success": True,
            "workers": workers,
            "count": len(workers)
        }
    except Exception as e:
        debug_log(f"列出 Worker 失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"列出 Worker 失败: {str(e)}"
        )


@router.post("/task-queue/cleanup")
async def cleanup_stale_tasks(max_idle_minutes: int = 30):
    """清理超时的运行中任务"""
    try:
        task_queue_db = get_task_queue_db()
        count = task_queue_db.cleanup_stale_tasks(max_idle_minutes=max_idle_minutes)
        
        return {
            "success": True,
            "cleaned_count": count,
            "message": f"清理了 {count} 个超时任务"
        }
    except Exception as e:
        debug_log(f"清理超时任务失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"清理超时任务失败: {str(e)}"
        )


@router.get("/task-queue/task-types")
async def list_task_types():
    """获取可用的任务类型列表"""
    try:
        from backend.infrastructure.execution.task_handlers import get_available_task_types
        task_types = get_available_task_types()
        
        return {
            "success": True,
            "task_types": task_types,
            "count": len(task_types)
        }
    except Exception as e:
        debug_log(f"获取任务类型列表失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"获取任务类型列表失败: {str(e)}"
        )


@router.get("/task-queue/task-types/{task_type}")
async def get_task_type_info(task_type: str):
    """获取特定任务类型的详细信息"""
    try:
        from backend.infrastructure.execution.task_handlers import get_task_type_info
        task_type_info = get_task_type_info(task_type)
        
        if not task_type_info:
            raise HTTPException(
                status_code=404,
                detail=f"任务类型不存在: {task_type}"
            )
        
        return {
            "success": True,
            "task_type": task_type_info
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"获取任务类型信息失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"获取任务类型信息失败: {str(e)}"
        )


# ========== 定时任务管理 API ==========

@router.post("/task-queue/scheduled-tasks")
async def create_scheduled_task(request: ScheduledTaskCreateRequest):
    """创建定时任务"""
    try:
        task_queue_db = get_task_queue_db()
        
        # 验证调度类型
        if request.schedule_type not in ["interval", "cron"]:
            raise HTTPException(
                status_code=400,
                detail="schedule_type 必须是 'interval' 或 'cron'"
            )
        
        # 验证调度配置
        if request.schedule_type == "interval":
            if "interval_seconds" not in request.schedule_config:
                raise HTTPException(
                    status_code=400,
                    detail="interval 类型需要 interval_seconds 配置"
                )
            interval = request.schedule_config.get("interval_seconds")
            if not isinstance(interval, int) or interval < 60:
                raise HTTPException(
                    status_code=400,
                    detail="interval_seconds 必须是大于等于 60 的整数"
                )
        
        schedule_id = task_queue_db.create_scheduled_task(
            task_type=request.task_type,
            task_name=request.task_name,
            schedule_type=request.schedule_type,
            schedule_config=request.schedule_config,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": "定时任务创建成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"创建定时任务失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"创建定时任务失败: {str(e)}"
        )


@router.get("/task-queue/scheduled-tasks")
async def list_scheduled_tasks(active_only: bool = False):
    """列出所有定时任务"""
    try:
        task_queue_db = get_task_queue_db()
        tasks = task_queue_db.list_scheduled_tasks(active_only=active_only)
        
        return {
            "success": True,
            "scheduled_tasks": tasks,
            "count": len(tasks)
        }
    except Exception as e:
        debug_log(f"列出定时任务失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"列出定时任务失败: {str(e)}"
        )


@router.get("/task-queue/scheduled-tasks/{schedule_id}")
async def get_scheduled_task(schedule_id: str):
    """获取定时任务详情"""
    try:
        task_queue_db = get_task_queue_db()
        tasks = task_queue_db.list_scheduled_tasks(active_only=False)
        
        task = next((t for t in tasks if t["schedule_id"] == schedule_id), None)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"定时任务 {schedule_id} 不存在"
            )
        
        return {
            "success": True,
            "scheduled_task": task
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"获取定时任务详情失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"获取定时任务详情失败: {str(e)}"
        )


@router.put("/task-queue/scheduled-tasks/{schedule_id}/toggle")
async def toggle_scheduled_task(schedule_id: str, is_active: bool):
    """启用/禁用定时任务"""
    try:
        task_queue_db = get_task_queue_db()
        success = task_queue_db.toggle_scheduled_task(schedule_id, is_active)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"定时任务 {schedule_id} 不存在"
            )
        
        return {
            "success": True,
            "message": f"定时任务已{'启用' if is_active else '禁用'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"切换定时任务状态失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"切换定时任务状态失败: {str(e)}"
        )


@router.delete("/task-queue/scheduled-tasks/{schedule_id}")
async def delete_scheduled_task(schedule_id: str):
    """删除定时任务"""
    try:
        task_queue_db = get_task_queue_db()
        success = task_queue_db.delete_scheduled_task(schedule_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"定时任务 {schedule_id} 不存在"
            )
        
        return {
            "success": True,
            "message": "定时任务已删除"
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"删除定时任务失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"删除定时任务失败: {str(e)}"
        )

