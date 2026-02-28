"""任务队列 API 路由"""
import logging
import re
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, File, UploadFile
from backend.infrastructure.storage.task_queue_db import (
    get_task_queue_db,
    TaskStatus,
    TaskPriority
)
from backend.infrastructure.pipeline_resolve import resolve_input_bindings_from_result
from backend.infrastructure.execution.task_handlers import (
    validate_task_creation,
    TASK_TYPES,
)
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
    depends_on_task_id: Optional[str] = None  # 上游任务 ID，管道用
    input_bindings: Optional[Dict[str, str]] = None  # 下游 metadata 字段 -> 上游 result 路径
    pipeline_id: Optional[str] = None  # 同一编排的组号，前端按组展示


def _generate_task_name(task_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """根据任务类型和参数自动生成任务名称"""
    from datetime import datetime
    ts = datetime.now().strftime("%m-%d %H:%M")
    meta = metadata or {}

    if task_type == "weather_query":
        loc = meta.get("location", "")
        qt = meta.get("query_type")
        fetch_forecast = meta.get("fetch_forecast") in (True, "true", "1", 1)
        fetch_current = meta.get("fetch_current") in (True, "true", "1", 1)
        if qt == "forecast" or (qt is None and fetch_forecast and not fetch_current):
            suffix = "天气预报"
        else:
            suffix = "天气查询"
        if loc:
            return f"{loc}{suffix} {ts}"
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

    if task_type == "mediawiki_write":
        t = meta.get("title", "")
        short = (t[:30] + "..." if len(t) > 30 else t) if t else "MediaWiki"
        return f"MediaWiki 写入 {short} {ts}"

    if task_type == "wechat_mp_draft":
        t = meta.get("title", "")
        short = (t[:20] + "…" if len(t) > 20 else t) if t else "公众号草稿"
        return f"公众号草稿 《{short}》 {ts}"

    type_names = {
        "weather_query": "天气查询",
        "video_download": "视频下载",
        "speech_to_text": "语音转文字",
        "video_extract_audio": "视频提取音频",
        "mediawiki_write": "MediaWiki 写入",
        "wechat_mp_draft": "公众号草稿",
    }
    name = type_names.get(task_type, task_type)
    return f"{name} {ts}"


class ScheduledTaskCreateRequest(BaseModel):
    task_type: str
    task_name: Optional[str] = ""  # 留空则自动生成
    schedule_type: str  # 'interval' 或 'cron'
    schedule_config: Dict[str, Any]  # {"interval_seconds": 3600} 或 cron 表达式
    metadata: Optional[Dict[str, Any]] = None


class ScheduledTaskUpdateRequest(BaseModel):
    task_name: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
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
        # 若有 input_bindings，绑定字段视为已提供，避免必填校验失败
        metadata_for_validation = dict(request.metadata or {})
        if request.input_bindings:
            for k in request.input_bindings:
                if k not in metadata_for_validation or metadata_for_validation[k] in (None, ""):
                    metadata_for_validation[k] = "(来自上游)"
        ok, err = validate_task_creation(request.task_type, metadata_for_validation)
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

        # 依赖与绑定：校验上游存在、未取消、无循环；input_bindings 的 key 须在 metadata_schema 中
        dep_id = (request.depends_on_task_id or "").strip() or None
        if dep_id:
            upstream = task_queue_db.get_task(dep_id)
            if not upstream:
                raise HTTPException(status_code=400, detail="上游任务不存在")
            if upstream.get("status") == TaskStatus.CANCELLED.value:
                raise HTTPException(status_code=400, detail="上游任务已取消")
            if task_queue_db.check_dependency_cycle(dep_id):
                raise HTTPException(status_code=400, detail="存在循环依赖")
        if request.input_bindings:
            schema = TASK_TYPES.get(request.task_type, {}).get("metadata_schema") or {}
            for key in request.input_bindings:
                if key not in schema:
                    raise HTTPException(
                        status_code=400,
                        detail=f"input_bindings 的键 '{key}' 不在任务类型 {request.task_type} 的 metadata_schema 中",
                    )
        
        # 创建任务（创建即入队，由 Worker 轮询拉取）
        pipeline_id = (request.pipeline_id or "").strip() or None
        task_id = task_queue_db.create_task(
            task_type=request.task_type,
            task_name=task_name,
            priority=priority,
            max_retries=request.max_retries or 3,
            metadata=request.metadata,
            depends_on_task_id=dep_id,
            input_bindings=request.input_bindings,
            pipeline_id=pipeline_id,
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


@router.get("/task-queue/tasks/{task_id}/queue-status")
async def get_task_queue_status(task_id: str):
    """
    诊断「为何带依赖的任务仍在待执行」：检查上游状态与 result 是否满足 acquire 条件。
    仅当任务 status=queued 且 depends_on_task_id 非空时返回上游信息。
    """
    try:
        task_queue_db = get_task_queue_db()
        task = task_queue_db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        dep_id = (task.get("depends_on_task_id") or "").strip() or None
        if task.get("status") != TaskStatus.QUEUED.value or not dep_id:
            return {
                "success": True,
                "task_id": task_id,
                "status": task.get("status"),
                "message": "仅对「待执行且存在依赖」的任务做衔接诊断",
                "upstream": None,
            }
        upstream = task_queue_db.get_task(dep_id)
        bindings = task.get("input_bindings") or {}
        upstream_status = upstream.get("status") if upstream else None
        upstream_result = upstream.get("result") if upstream else None
        upstream_has_result = upstream_result is not None and (upstream_result != "" if isinstance(upstream_result, str) else True)
        # 检查上游 result 是否包含绑定路径所需字段（如 result.data.output_file）
        resolved = resolve_input_bindings_from_result(upstream_result, bindings) if upstream_has_result and bindings else {}
        missing_bindings = [k for k in bindings if not resolved.get(k)]
        can_acquire = (
            upstream_status == TaskStatus.COMPLETED.value
            and upstream_has_result
            and len(missing_bindings) == 0
        )
        message = (
            "下游可被拉取" if can_acquire
            else "上游未找到，无法衔接" if not upstream
            else f"上游状态={upstream_status}，result 非空={upstream_has_result}"
            + (f"；绑定缺失: {missing_bindings}" if missing_bindings else "")
        )
        return {
            "success": True,
            "task_id": task_id,
            "status": task.get("status"),
            "depends_on_task_id": dep_id,
            "message": message,
            "can_acquire": can_acquire,
            "upstream": {
                "task_id": dep_id,
                "found": upstream is not None,
                "status": upstream_status,
                "has_result": upstream_has_result,
                "resolved_bindings": resolved if bindings else None,
                "missing_bindings": missing_bindings or None,
            } if dep_id else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"queue-status 失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")


@router.patch("/task-queue/tasks/{task_id}/patch-result-output-file")
async def patch_task_result_output_file(task_id: str):
    """
    为已完成的「视频下载」等任务补全 result.data.output_file（从 result.data.output_dir 推断），
    使其满足管道下游绑定 result.data.output_file 的设计。支持 8 位短 id（如 af0a871c）。
    """
    try:
        from pathlib import Path
        from backend.core.agent.tools.builtin.video_downloader_tool import _find_single_output_file

        task_queue_db = get_task_queue_db()
        resolved_id = task_id.strip()
        if len(resolved_id) == 8:
            full_id = task_queue_db.get_task_id_by_prefix(resolved_id)
            if full_id:
                resolved_id = full_id
        task = task_queue_db.get_task(resolved_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        if task.get("status") != TaskStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400,
                detail=f"仅支持对已完成任务补全 result；当前状态: {task.get('status')}",
            )
        result = task.get("result")
        if not result or not isinstance(result, dict):
            raise HTTPException(status_code=400, detail="任务无 result 或格式无效")
        data = dict(result.get("data") or {})
        if data.get("output_file"):
            return {"success": True, "message": "result.data.output_file 已存在", "task_id": resolved_id}
        output_dir = data.get("output_dir")
        if not output_dir:
            raise HTTPException(
                status_code=400,
                detail="result.data 中无 output_dir，无法推断 output_file",
            )
        out_path = _find_single_output_file(Path(output_dir))
        if not out_path:
            raise HTTPException(
                status_code=404,
                detail=f"在 output_dir 下未找到视频/音频文件: {output_dir}",
            )
        data["output_file"] = out_path
        new_result = {**result, "data": data}
        if not task_queue_db.update_task_result(resolved_id, new_result):
            raise HTTPException(status_code=500, detail="更新 result 失败")
        return {
            "success": True,
            "message": "已补全 result.data.output_file",
            "task_id": resolved_id,
            "output_file": out_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"patch-result-output-file 失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"补全失败: {str(e)}")


@router.get("/task-queue/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务信息。若任务有依赖且为 running/completed，则附带 resolved_metadata（执行前解析后的 metadata）便于排查。"""
    try:
        task_queue_db = get_task_queue_db()
        task = task_queue_db.get_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"任务不存在: {task_id}"
            )
        dep_id = (task.get("depends_on_task_id") or "").strip() or None
        bindings = task.get("input_bindings")
        if dep_id and bindings and task.get("status") in (TaskStatus.RUNNING.value, TaskStatus.COMPLETED.value):
            upstream = task_queue_db.get_task(dep_id)
            if upstream and upstream.get("result"):
                task = dict(task)
                task["resolved_metadata"] = resolve_input_bindings_from_result(
                    upstream.get("result"), bindings
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
    offset: int = 0,
    deleted: Optional[str] = None,
    created_by_schedule_id: Optional[str] = None,
):
    """列出任务。deleted=only 时仅返回已软删除任务；不传或 exclude 时仅返回未删除。created_by_schedule_id 可筛选某定时任务创建的任务。"""
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
        include_deleted = None
        if deleted == "only":
            include_deleted = "only"
        elif deleted and deleted != "exclude":
            raise HTTPException(status_code=400, detail="deleted 仅支持 only 或 exclude")
        
        tasks = task_queue_db.list_tasks(
            status=task_status,
            limit=limit,
            offset=offset,
            include_deleted=include_deleted,
            created_by_schedule_id=created_by_schedule_id or None,
            include_result=bool(created_by_schedule_id),
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


@router.post("/task-queue/tasks/{task_id}/requeue")
async def requeue_task(task_id: str):
    """将已失败且带依赖的任务重新入队（清空错误），用上游最新 result 再执行一次。支持 8 位短 id。"""
    try:
        task_queue_db = get_task_queue_db()
        resolved_id = task_id.strip()
        if len(resolved_id) == 8:
            full_id = task_queue_db.get_task_id_by_prefix(resolved_id)
            if full_id:
                resolved_id = full_id
        task = task_queue_db.get_task(resolved_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        if task.get("status") != TaskStatus.FAILED.value:
            raise HTTPException(
                status_code=400,
                detail=f"仅支持对已失败任务重新入队；当前状态: {task.get('status')}",
            )
        if not task_queue_db.requeue_failed_task(resolved_id):
            raise HTTPException(status_code=400, detail="重新入队失败（可能状态已变更）")
        return {
            "success": True,
            "message": "已重新入队，待 Worker 拉取后会用上游最新 result 执行",
            "task_id": resolved_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"requeue 失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"重新入队失败: {str(e)}")


@router.post("/task-queue/tasks/{task_id}/restart")
async def restart_task(task_id: str):
    """将已完成或已失败的任务原地重置为待执行：只修改状态与执行结果，不新开任务。"""
    try:
        task_queue_db = get_task_queue_db()
        resolved_id = task_id.strip()
        if len(resolved_id) == 8:
            full_id = task_queue_db.get_task_id_by_prefix(resolved_id)
            if full_id:
                resolved_id = full_id
        task = task_queue_db.get_task(resolved_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        status = task.get("status")
        if status not in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
            raise HTTPException(
                status_code=400,
                detail=f"仅支持对已完成或已失败的任务重新开始，当前状态: {status}",
            )
        ok = task_queue_db.reset_task_to_queued(resolved_id)
        if not ok:
            raise HTTPException(status_code=500, detail="重置任务失败")
        return {
            "success": True,
            "task_id": resolved_id,
            "message": "任务已重置为待执行",
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


@router.post("/task-queue/tasks/{task_id}/soft-delete")
async def soft_delete_task(task_id: str):
    """软删除任务：任务进入回收站，可恢复。仅允许对非运行中的任务操作。"""
    try:
        task_queue_db = get_task_queue_db()
        resolved_id = task_id.strip()
        if len(resolved_id) == 8:
            full_id = task_queue_db.get_task_id_by_prefix(resolved_id)
            if full_id:
                resolved_id = full_id
        task = task_queue_db.get_task(resolved_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        if task.get("deleted_at"):
            raise HTTPException(status_code=400, detail="任务已在回收站中")
        if task.get("status") == TaskStatus.RUNNING.value:
            raise HTTPException(status_code=400, detail="请先取消运行中的任务再删除")
        success = task_queue_db.soft_delete_task(resolved_id)
        if not success:
            raise HTTPException(status_code=400, detail="软删除失败（可能状态已变更）")
        return {"success": True, "message": "已移入回收站", "task_id": resolved_id}
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"软删除任务失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"软删除失败: {str(e)}")


@router.post("/task-queue/tasks/{task_id}/restore")
async def restore_task(task_id: str):
    """从回收站恢复任务。"""
    try:
        task_queue_db = get_task_queue_db()
        resolved_id = task_id.strip()
        if len(resolved_id) == 8:
            full_id = task_queue_db.get_task_id_by_prefix(resolved_id)
            if full_id:
                resolved_id = full_id
        task = task_queue_db.get_task(resolved_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        if not task.get("deleted_at"):
            raise HTTPException(status_code=400, detail="任务未在回收站中，无需恢复")
        success = task_queue_db.restore_task(resolved_id)
        if not success:
            raise HTTPException(status_code=400, detail="恢复失败（可能状态已变更）")
        return {"success": True, "message": "已恢复", "task_id": resolved_id}
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"恢复任务失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")


@router.delete("/task-queue/tasks/{task_id}")
async def delete_task(task_id: str):
    """彻底删除任务（物理删除）。仅允许删除 queued/completed/failed/cancelled；running 需先取消再删除。"""
    try:
        task_queue_db = get_task_queue_db()
        resolved_id = task_id.strip()
        if len(resolved_id) == 8:
            full_id = task_queue_db.get_task_id_by_prefix(resolved_id)
            if full_id:
                resolved_id = full_id
        task = task_queue_db.get_task(resolved_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        if task.get("status") == TaskStatus.RUNNING.value:
            raise HTTPException(
                status_code=400,
                detail="请先取消运行中的任务再删除",
            )
        success = task_queue_db.delete_task(resolved_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除任务失败")
        return {
            "success": True,
            "message": "任务已删除",
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"删除任务失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


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
    """获取特定任务类型的详细信息（含 pipeline_outputs、metadata_schema 中的 pipeline_accept）"""
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


@router.get("/task-queue/task-types/{task_type}/linkable-upstreams")
async def get_linkable_upstreams(task_type: str):
    """获取可作为管道上游的任务类型及推荐绑定（根据 pipeline_outputs / pipeline_accept 判断可链接性）"""
    try:
        from backend.infrastructure.execution.task_handlers import get_task_type_info, get_linkable_upstream_types
        if not get_task_type_info(task_type):
            raise HTTPException(status_code=404, detail=f"任务类型不存在: {task_type}")
        result = get_linkable_upstream_types(task_type)
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"获取可链接上游失败: {str(e)}", level="error")
        raise HTTPException(
            status_code=500,
            detail=f"获取可链接上游失败: {str(e)}"
        )


def _sanitize_upload_filename(name: str) -> str:
    """只保留安全字符，避免路径穿越；保留扩展名。"""
    name = (name or "file").strip()
    stem = Path(name).stem
    ext = (Path(name).suffix or "").strip()
    ext = re.sub(r"[^\w.\-]", "", ext)[:20]
    safe_stem = re.sub(r"[^\w\u4e00-\u9fff.\- ]", "_", stem)[:180] or "file"
    suffix = "_" + uuid.uuid4().hex[:8] if len(stem) > 160 else ""
    return safe_stem + suffix + (("." + ext) if ext else "")


@router.post("/task-queue/upload-input-file")
async def upload_input_file(file: UploadFile = File(...)):
    """
    上传输入文件到用户主目录下的 hou-cli/task-uploads，供语音转文字/视频提音频等任务使用。
    返回保存后的绝对路径，前端可将其填入 input_file。
    """
    home = Path.home().resolve()
    upload_dir = home / "hou-cli" / "task-uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_upload_filename(file.filename or "upload")
    dest = (upload_dir / safe_name).resolve()
    try:
        dest.relative_to(home)
    except ValueError:
        raise HTTPException(status_code=400, detail="上传目录必须在用户主目录下")
    try:
        content = await file.read()
        dest.write_bytes(content)
    except Exception as e:
        logger.exception("上传写入失败: %s", e)
        raise HTTPException(status_code=500, detail=f"保存文件失败: {e}")
    return {"success": True, "path": str(dest)}


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
            if not isinstance(interval, (int, float)) or interval < 60:
                raise HTTPException(
                    status_code=400,
                    detail="interval_seconds 必须是大于等于 60 的数字"
                )
        elif request.schedule_type == "cron":
            if not (request.schedule_config.get("cron") or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail="cron 类型需要 schedule_config.cron 非空"
                )

        # 校验 task_type 与 metadata（与普通任务创建共用）
        ok, err = validate_task_creation(
            request.task_type,
            request.metadata or {},
        )
        if not ok:
            raise HTTPException(status_code=400, detail=err or "任务参数校验失败")

        task_name = (request.task_name or "").strip()
        if not task_name:
            type_names = {"weather_query": "天气查询", "video_download": "视频下载", "speech_to_text": "语音转文字", "video_extract_audio": "视频提取音频", "mediawiki_write": "MediaWiki 写入", "wechat_mp_draft": "公众号草稿"}
            task_name = f"{type_names.get(request.task_type, request.task_type)}_定时"

        schedule_id = task_queue_db.create_scheduled_task(
            task_type=request.task_type,
            task_name=task_name,
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


@router.post("/task-queue/scheduled-tasks/{schedule_id}/run-now")
async def run_scheduled_task_now(schedule_id: str):
    """立即执行定时任务：创建任务入队，并重新计算下次运行时间"""
    try:
        task_queue_db = get_task_queue_db()
        tasks = task_queue_db.list_scheduled_tasks(active_only=False)
        scheduled_task = next((t for t in tasks if t["schedule_id"] == schedule_id), None)
        if not scheduled_task:
            raise HTTPException(status_code=404, detail=f"定时任务 {schedule_id} 不存在")

        from shared.time_utils import utc_now_iso

        ok, err = validate_task_creation(
            scheduled_task["task_type"],
            scheduled_task.get("metadata", {}),
        )
        if not ok:
            raise HTTPException(status_code=400, detail=err or "任务参数校验失败")

        task_id = task_queue_db.create_task(
            task_type=scheduled_task["task_type"],
            task_name=scheduled_task["task_name"],
            priority=TaskPriority.NORMAL,
            metadata=scheduled_task.get("metadata", {}),
            created_by_schedule_id=schedule_id,
        )

        now = utc_now_iso()
        task_queue_db.update_scheduled_task_after_success(
            schedule_id=schedule_id,
            schedule_type=scheduled_task["schedule_type"],
            schedule_config=scheduled_task["schedule_config"],
            last_run_time=now,
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "已立即创建任务，下次运行时间已更新",
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"立即执行定时任务失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"立即执行失败: {str(e)}")


@router.patch("/task-queue/scheduled-tasks/{schedule_id}")
async def update_scheduled_task(schedule_id: str, request: ScheduledTaskUpdateRequest):
    """更新定时任务参数（任务名称、调度配置、metadata）"""
    try:
        task_queue_db = get_task_queue_db()
        tasks = task_queue_db.list_scheduled_tasks(active_only=False)
        task = next((t for t in tasks if t["schedule_id"] == schedule_id), None)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务 {schedule_id} 不存在")

        if request.schedule_type is not None or request.schedule_config is not None:
            st = request.schedule_type or task["schedule_type"]
            cfg = request.schedule_config if request.schedule_config is not None else task.get("schedule_config", {})
            if st not in ["interval", "cron"]:
                raise HTTPException(status_code=400, detail="schedule_type 必须是 'interval' 或 'cron'")
            if st == "interval":
                if "interval_seconds" not in cfg:
                    raise HTTPException(status_code=400, detail="interval 类型需要 interval_seconds")
                sec = cfg.get("interval_seconds")
                if not isinstance(sec, (int, float)) or sec < 60:
                    raise HTTPException(status_code=400, detail="interval_seconds 必须 >= 60")
            elif st == "cron":
                if not (cfg.get("cron") or "").strip():
                    raise HTTPException(status_code=400, detail="cron 类型需要 cron 表达式非空")

        if request.metadata is not None:
            ok, err = validate_task_creation(task["task_type"], request.metadata)
            if not ok:
                raise HTTPException(status_code=400, detail=err or "任务参数校验失败")

        success = task_queue_db.update_scheduled_task(
            schedule_id=schedule_id,
            task_name=request.task_name,
            schedule_type=request.schedule_type,
            schedule_config=request.schedule_config,
            metadata=request.metadata,
        )
        if not success:
            raise HTTPException(status_code=404, detail="更新失败")

        return {"success": True, "message": "定时任务已更新"}
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"更新定时任务失败: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=str(e))


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

