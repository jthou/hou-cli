"""任务管理器 - 管理长时间运行的任务，支持进度查询和状态管理"""
import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    task_name: str
    status: TaskStatus
    progress: int = 0  # 0-100
    message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata
        }


class TaskManager:
    """任务管理器（单例）"""
    
    _instance: Optional['TaskManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._tasks: Dict[str, TaskInfo] = {}
        self._task_handles: Dict[str, asyncio.Task] = {}
    
    async def create_task(
        self,
        task_name: str,
        task_func: Callable,
        *args,
        **kwargs
    ) -> str:
        """
        创建并启动任务
        
        Args:
            task_name: 任务名称
            task_func: 任务函数（异步）
            *args, **kwargs: 传递给任务函数的参数
            
        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name=task_name,
            status=TaskStatus.PENDING
        )
        
        async def _run_task():
            """运行任务的包装函数"""
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = datetime.now()
            
            try:
                # 如果任务函数接受 task_info 参数，传递它
                if 'task_info' in kwargs or any('task_info' in str(p) for p in task_func.__code__.co_varnames):
                    kwargs['task_info'] = task_info
                
                result = await task_func(*args, **kwargs)
                task_info.status = TaskStatus.COMPLETED
                task_info.result = result
                task_info.progress = 100
                task_info.message = "任务完成"
            except asyncio.CancelledError:
                task_info.status = TaskStatus.CANCELLED
                task_info.message = "任务已取消"
            except Exception as e:
                task_info.status = TaskStatus.FAILED
                task_info.error = str(e)
                task_info.message = f"任务失败: {str(e)}"
                logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
            finally:
                task_info.completed_at = datetime.now()
                # 清理任务句柄
                if task_id in self._task_handles:
                    del self._task_handles[task_id]
        
        self._tasks[task_id] = task_info
        task_handle = asyncio.create_task(_run_task())
        self._task_handles[task_id] = task_handle
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self._tasks.get(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> list[TaskInfo]:
        """列出任务"""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self._task_handles:
            return False
        
        task_handle = self._task_handles[task_id]
        task_handle.cancel()
        
        try:
            await task_handle
        except asyncio.CancelledError:
            pass
        
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.CANCELLED
        
        return True
    
    def update_task_progress(
        self,
        task_id: str,
        progress: int,
        message: str = ""
    ) -> bool:
        """更新任务进度"""
        if task_id not in self._tasks:
            return False
        
        task_info = self._tasks[task_id]
        # 确保 progress 是整数类型
        if isinstance(progress, str):
            try:
                progress = int(progress)
            except (ValueError, TypeError):
                # 如果无法转换，使用当前进度或默认值
                progress = task_info.progress if hasattr(task_info, 'progress') else 0
        elif not isinstance(progress, (int, float)):
            progress = task_info.progress if hasattr(task_info, 'progress') else 0
        else:
            progress = int(progress)
        
        task_info.progress = max(0, min(100, progress))
        if message:
            task_info.message = message
        
        return True
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务（超过指定时间）"""
        now = datetime.now()
        to_remove = []
        
        for task_id, task_info in self._tasks.items():
            if task_info.completed_at:
                age = (now - task_info.completed_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            if task_id in self._tasks:
                del self._tasks[task_id]
            if task_id in self._task_handles:
                # 如果任务还在运行，先取消
                task_handle = self._task_handles[task_id]
                if not task_handle.done():
                    task_handle.cancel()
                del self._task_handles[task_id]
        
        logger.info(f"清理了 {len(to_remove)} 个旧任务")


# 全局任务管理器实例
task_manager = TaskManager()

