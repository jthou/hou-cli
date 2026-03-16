"""心跳监控模块"""
import asyncio
import logging
import time
import psutil
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
from backend.infrastructure.storage.task_queue_db import TaskPriority
from shared.time_utils import utc_now_iso, utc_now

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    """心跳监控器"""
    
    def __init__(self, interval: int = 30):
        """
        初始化心跳监控器
        
        Args:
            interval: 心跳间隔（秒），默认 30 秒
        """
        self.interval = interval
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.last_heartbeat: Optional[datetime] = None
        self.heartbeat_count = 0
        self.start_time = datetime.now()
        
        # 系统指标
        self.metrics = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_used_mb": 0.0,
            "uptime_seconds": 0,
        }
    
    async def start(self):
        """启动心跳监控"""
        if self.is_running:
            logger.warning("心跳监控已在运行")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        self.task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"心跳监控已启动，间隔: {self.interval} 秒")
    
    async def stop(self):
        """停止心跳监控"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("心跳监控已停止")
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        # 延迟导入，避免循环依赖
        task_queue_db = None
        
        while self.is_running:
            try:
                await self._collect_metrics()
                self.last_heartbeat = datetime.now()
                self.heartbeat_count += 1
                
                # 延迟加载 task_queue_db（首次心跳时加载）
                if task_queue_db is None:
                    try:
                        from backend.infrastructure.storage.task_queue_db import (
                            get_task_queue_db,
                        )
                        task_queue_db = get_task_queue_db()
                    except Exception:
                        pass

                if task_queue_db:
                    # 每 10 次心跳监控一次 Worker 健康状态
                    if self.heartbeat_count % 10 == 0:
                        await self.monitor_workers(
                            task_queue_db, max_silence_seconds=120
                        )
                    # 每次心跳都检查定时任务
                    await self.check_scheduled_tasks(task_queue_db)
                    
                    logger.debug(
                        f"心跳 #{self.heartbeat_count} - "
                        f"CPU: {self.metrics['cpu_percent']:.1f}%, "
                        f"内存: {self.metrics['memory_percent']:.1f}%"
                    )
                
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳监控错误: {e}", exc_info=True)
                await asyncio.sleep(self.interval)
    
    async def _collect_metrics(self):
        """收集系统指标"""
        try:
            # 在后台线程中执行 CPU 和内存检查（避免阻塞）
            loop = asyncio.get_event_loop()
            cpu_percent = await loop.run_in_executor(
                None, psutil.cpu_percent, 1.0
            )
            memory = await loop.run_in_executor(
                None, psutil.virtual_memory
            )
            
            self.metrics.update({
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            })
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}", exc_info=True)
    
    def get_status(self) -> Dict:
        """获取心跳状态"""
        return {
            "is_running": self.is_running,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "heartbeat_count": self.heartbeat_count,
            "uptime_seconds": self.metrics.get("uptime_seconds", 0),
            "metrics": self.metrics.copy(),
        }
    
    def is_healthy(self, max_silence_seconds: int = 60) -> bool:
        """
        检查是否健康
        
        Args:
            max_silence_seconds: 最大静默时间（秒），超过此时间认为不健康
        
        Returns:
            是否健康
        """
        if not self.is_running or self.last_heartbeat is None:
            return False
        
        silence = (datetime.now() - self.last_heartbeat).total_seconds()
        return silence < max_silence_seconds
    
    async def monitor_workers(self, task_queue_db, max_silence_seconds: int = 120):
        """
        监控 Worker 健康状态（在心跳循环中调用）
        
        Args:
            task_queue_db: 任务队列数据库实例
            max_silence_seconds: Worker 最大静默时间（秒）
        """
        try:
            workers = task_queue_db.list_workers()
            now = utc_now()  # Worker 的 last_heartbeat 存的是 UTC，需统一时区
            for worker in workers:
                last_heartbeat_str = worker.get("last_heartbeat")
                if not last_heartbeat_str:
                    continue
                
                try:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
                    # 2025-03-15：兼容 naive datetime，避免 can't subtract offset-naive and offset-aware
                    if last_heartbeat.tzinfo is None:
                        last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)
                    silence = (now - last_heartbeat).total_seconds()
                    
                    # 如果 Worker 超过最大静默时间，清理其任务
                    if silence > max_silence_seconds:
                        worker_id = worker.get("worker_id")
                        current_task_id = worker.get("current_task_id")
                        
                        if current_task_id:
                            logger.warning(
                                f"Worker {worker_id} 心跳超时 ({silence:.0f}秒)，"
                                f"清理任务 {current_task_id}"
                            )
                            # 清理超时任务（重新入队）
                            task_queue_db.cleanup_stale_tasks(max_idle_minutes=int(silence / 60))
                except Exception as e:
                    logger.error(f"监控 Worker {worker.get('worker_id')} 失败: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"监控 Worker 健康状态失败: {e}", exc_info=True)
    
    async def check_scheduled_tasks(self, task_queue_db):
        """
        检查并执行到期的定时任务（在心跳循环中调用）
        失败时应用错误退避，成功时重置 consecutive_errors。
        """
        try:
            due_tasks = task_queue_db.get_due_scheduled_tasks()
            if not due_tasks:
                return

            logger.info(f"发现 {len(due_tasks)} 个到期的定时任务")

            for scheduled_task in due_tasks:
                schedule_id = scheduled_task.get("schedule_id")
                try:
                    # 1. 校验 task_type 与 metadata（与 API 创建共用）
                    from backend.infrastructure.execution.task_handlers import (
                        validate_task_creation,
                    )
                    ok, err = validate_task_creation(
                        scheduled_task["task_type"],
                        scheduled_task.get("metadata", {}),
                    )
                    if not ok:
                        task_queue_db.update_scheduled_task_on_failure(
                            schedule_id=schedule_id,
                            error=err or "校验失败",
                        )
                        continue

                    # 2. 创建任务
                    task_id = task_queue_db.create_task(
                        task_type=scheduled_task["task_type"],
                        task_name=scheduled_task["task_name"],
                        priority=TaskPriority.NORMAL,
                        metadata=scheduled_task.get("metadata", {}),
                        created_by_schedule_id=schedule_id,
                    )

                    # 3. 更新成功状态
                    now = utc_now_iso()
                    task_queue_db.update_scheduled_task_after_success(
                        schedule_id=schedule_id,
                        schedule_type=scheduled_task["schedule_type"],
                        schedule_config=scheduled_task["schedule_config"],
                        last_run_time=now,
                    )

                    logger.info(
                        f"定时任务 {schedule_id} 已创建任务 "
                        f"{task_id} ({scheduled_task['task_name']})"
                    )
                except Exception as e:
                    logger.error(
                        f"执行定时任务 {schedule_id} 失败: {e}",
                        exc_info=True,
                    )
                    task_queue_db.update_scheduled_task_on_failure(
                        schedule_id=schedule_id,
                        error=str(e),
                    )
        except Exception as e:
            logger.error(f"检查定时任务失败: {e}", exc_info=True)


# 全局心跳监控器实例
_heartbeat_monitor: Optional[HeartbeatMonitor] = None


def get_heartbeat_monitor(interval: int = 30) -> HeartbeatMonitor:
    """获取全局心跳监控器实例"""
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor(interval=interval)
    return _heartbeat_monitor

