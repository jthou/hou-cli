"""任务 Worker 进程管理器"""
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from backend.infrastructure.storage.task_queue_db import (
    get_task_queue_db,
    TaskStatus,
    TaskQueueDB
)
from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
from shared.debug_utils import debug_log

logger = logging.getLogger(__name__)


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
            # 查找任务处理器
            handler = self.task_handlers.get(task_type)
            
            if not handler:
                error_msg = f"未找到任务类型 '{task_type}' 的处理器"
                logger.error(error_msg)
                self.task_queue_db.complete_task(task_id, error=error_msg)
                self.current_task_id = None
                return
            
            # 执行任务
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

