"""任务 Worker 进程管理器"""
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from backend.infrastructure.pipeline_resolve import resolve_input_bindings_from_result
from backend.infrastructure.storage.task_queue_db import (
    get_task_queue_db,
    TaskStatus,
    TaskQueueDB
)
from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
from shared.debug_utils import debug_log

logger = logging.getLogger(__name__)

# 任务类型超时（秒），超时则标记失败
TASK_TIMEOUT_SECONDS = {
    "video_download": 30 * 60,       # 30 分钟
    "weather_query": 60,             # 1 分钟
    "web_search": 60,                # 1 分钟
    "speech_to_text": 60 * 60,       # 1 小时
    "video_extract_audio": 30 * 60,  # 30 分钟
    "mediawiki_write": 5 * 60,       # 5 分钟
    "wechat_mp_draft": 60,           # 1 分钟
    "url_to_wiki": 15 * 60,          # 15 分钟（抓取 + 翻译 + 写入）
    "pdf_to_wiki": 60 * 60,          # 60 分钟（下载 + 拆分 + 转文字 + 翻译 + 写入）
    "wiki_directory_refresh": 5 * 60,  # 5 分钟（查任务 + 生成目录 + 写入）
}


class TaskWorker:
    """任务 Worker - 从数据库队列中获取并执行任务"""
    
    def __init__(
        self,
        worker_name: Optional[str] = None,
        poll_interval: int = 5,
        heartbeat_interval: int = 30
    ):
        """
        初始化 Task Worker
        
        Args:
            worker_name: Worker 名称
            poll_interval: 轮询间隔（秒）
            heartbeat_interval: 心跳间隔（秒）
        """
        self.worker_id = str(uuid.uuid4())
        self.worker_name = worker_name or f"worker-{self.worker_id[:8]}"
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        self.task_queue_db: TaskQueueDB = get_task_queue_db()
        self.heartbeat_monitor = get_heartbeat_monitor(interval=heartbeat_interval)
        
        # 任务处理器注册表
        self.task_handlers: Dict[str, Callable] = {}
        
        # 当前执行的任务
        self.current_task_id: Optional[str] = None
        self.current_task_handle: Optional[asyncio.Task] = None
    
    def register_handler(self, task_type: str, handler: Callable):
        """
        注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数，签名: async def handler(task_info: Dict[str, Any]) -> Any
        """
        self.task_handlers[task_type] = handler
        debug_log(f"注册任务处理器: {task_type}")
    
    async def start(self):
        """启动 Worker"""
        if self.is_running:
            logger.warning(f"Worker {self.worker_id} 已在运行")
            return
        
        # 注册 Worker
        self.task_queue_db.register_worker(self.worker_id, self.worker_name)
        
        # 启动心跳监控
        await self.heartbeat_monitor.start()
        
        # 启动 Worker 主循环
        self.is_running = True
        self.task = asyncio.create_task(self._worker_loop())
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"Worker {self.worker_id} ({self.worker_name}) 已启动")
    
    async def stop(self):
        """停止 Worker"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 取消当前任务
        if self.current_task_handle and not self.current_task_handle.done():
            self.current_task_handle.cancel()
            try:
                await self.current_task_handle
            except asyncio.CancelledError:
                pass
        
        # 停止心跳
        await self.heartbeat_monitor.stop()
        
        # 停止主循环
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Worker {self.worker_id} 已停止")
    
    async def _heartbeat_loop(self):
        """心跳循环 - 定期更新 Worker 心跳"""
        while self.is_running:
            try:
                self.task_queue_db.update_worker_heartbeat(self.worker_id)
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker 心跳更新失败: {e}", exc_info=True)
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _worker_loop(self):
        """Worker 主循环 - 从队列获取任务并执行"""
        while self.is_running:
            try:
                # 如果当前没有任务在执行，尝试获取新任务
                if self.current_task_id is None:
                    task_info = self.task_queue_db.acquire_task(self.worker_id)
                    
                    if task_info:
                        self.current_task_id = task_info["task_id"]
                        self.current_task_handle = asyncio.create_task(
                            self._execute_task(task_info)
                        )
                    else:
                        # 没有可用任务，等待一段时间后重试
                        await asyncio.sleep(self.poll_interval)
                else:
                    # 有任务在执行，等待一段时间后检查
                    await asyncio.sleep(self.poll_interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker 循环错误: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    def _resolve_input_bindings(self, task_info: Dict[str, Any]) -> None:
        """
        若有 depends_on_task_id 与 input_bindings，从上游任务 result 按点号路径解析并合并进 task_info["metadata"]。
        """
        dep_id = (task_info.get("depends_on_task_id") or "").strip() or None
        bindings = task_info.get("input_bindings")
        if not dep_id or not bindings or not isinstance(bindings, dict):
            return
        upstream = self.task_queue_db.get_task(dep_id)
        if not upstream or not upstream.get("result"):
            return
        metadata = dict(task_info.get("metadata") or {})
        resolved = resolve_input_bindings_from_result(upstream.get("result"), bindings)
        metadata.update(resolved)
        task_info["metadata"] = metadata

    def _check_pipeline_input_match(self, task_info: Dict[str, Any]) -> Optional[str]:
        """
        若有 input_bindings，检查其中在 metadata_schema 里为 required 的字段是否都有非空值。
        Returns: 若匹配则 None；若不匹配返回错误描述（用于 complete_task(error=...)）。
        """
        bindings = task_info.get("input_bindings")
        if not bindings or not isinstance(bindings, dict):
            return None
        task_type = task_info.get("task_type")
        from backend.infrastructure.execution.task_handlers import TASK_TYPES
        schema = (TASK_TYPES.get(task_type) or {}).get("metadata_schema") or {}
        metadata = task_info.get("metadata") or {}
        for key in bindings:
            if key not in schema:
                continue
            field_spec = schema[key] if isinstance(schema.get(key), dict) else {}
            if not field_spec.get("required"):
                continue
            val = metadata.get(key)
            if val is None:
                return f"管道输入不匹配：上游 result 未解析到必填字段 '{key}'（path: {bindings.get(key)}）"
            if isinstance(val, str) and not val.strip():
                return f"管道输入不匹配：必填字段 '{key}' 解析结果为空（path: {bindings.get(key)}）"
        return None

    async def _execute_task(self, task_info: Dict[str, Any]):
        """
        执行任务
        
        Args:
            task_info: 任务信息
        """
        task_id = task_info["task_id"]
        task_type = task_info["task_type"]
        task_name = task_info["task_name"]
        
        logger.info(f"Worker {self.worker_id} 开始执行任务: {task_id} ({task_name})")
        
        try:
            # 管道：从上游 result 解析 input_bindings 并合并进 metadata
            self._resolve_input_bindings(task_info)
            # 管道：检查由 input_bindings 提供的必填字段是否都有值，缺失则直接失败
            match_err = self._check_pipeline_input_match(task_info)
            if match_err:
                logger.error(f"任务 {task_id} {match_err}")
                self.task_queue_db.complete_task(task_id, error=match_err)
                self.current_task_id = None
                return

            # 查找任务处理器
            handler = self.task_handlers.get(task_type)
            
            if not handler:
                error_msg = f"未找到任务类型 '{task_type}' 的处理器"
                logger.error(error_msg)
                self.task_queue_db.complete_task(task_id, error=error_msg)
                self.current_task_id = None
                return
            
            # 执行任务（部分类型设超时，避免长时间占用 Worker）
            timeout = TASK_TIMEOUT_SECONDS.get(task_type)
            if timeout is not None:
                try:
                    result = await asyncio.wait_for(handler(task_info), timeout=timeout)
                except asyncio.TimeoutError:
                    error_msg = f"任务执行超时（超过 {timeout // 60} 分钟）"
                    logger.error(f"任务 {task_id} {error_msg}")
                    self.task_queue_db.complete_task(
                        task_id,
                        result={"status": "error", "summary": "执行超时", "error": {"code": "TIMEOUT", "message": error_msg, "details": ""}},
                    )
                    return
            else:
                result = await handler(task_info)
            
            # 任务完成
            self.task_queue_db.complete_task(task_id, result=result)
            logger.info(f"Worker {self.worker_id} 完成任务: {task_id}")
            
        except asyncio.CancelledError:
            # 任务被取消
            logger.warning(f"任务 {task_id} 被取消")
            self.task_queue_db.cancel_task(task_id)
            
        except Exception as e:
            # 任务执行失败
            error_msg = str(e)
            logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
            self.task_queue_db.complete_task(task_id, error=error_msg)
            
        finally:
            # 清理当前任务
            self.current_task_id = None
            self.current_task_handle = None
    
    def update_task_progress(self, progress: int, message: Optional[str] = None):
        """
        更新当前任务的进度
        
        Args:
            progress: 进度（0-100）
            message: 进度消息
        """
        if self.current_task_id:
            self.task_queue_db.update_task_progress(
                self.current_task_id,
                progress,
                message
            )
    
    def get_status(self) -> Dict[str, Any]:
        """获取 Worker 状态"""
        return {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "is_running": self.is_running,
            "current_task_id": self.current_task_id,
            "registered_handlers": list(self.task_handlers.keys()),
            "heartbeat": self.heartbeat_monitor.get_status()
        }


# 全局 Worker 实例
_global_worker: Optional[TaskWorker] = None


def get_task_worker(
    worker_name: Optional[str] = None,
    poll_interval: int = 5,
    heartbeat_interval: int = 30
) -> TaskWorker:
    """
    获取全局 Task Worker 实例
    
    Args:
        worker_name: Worker 名称
        poll_interval: 轮询间隔（秒）
        heartbeat_interval: 心跳间隔（秒）
        
    Returns:
        TaskWorker 实例
    """
    global _global_worker
    if _global_worker is None:
        _global_worker = TaskWorker(
            worker_name=worker_name,
            poll_interval=poll_interval,
            heartbeat_interval=heartbeat_interval
        )
    return _global_worker

