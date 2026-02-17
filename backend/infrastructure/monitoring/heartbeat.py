"""心跳监控模块"""
import asyncio
import logging
import time
import psutil
from typing import Dict, Optional
from datetime import datetime, timedelta

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
        while self.is_running:
            try:
                await self._collect_metrics()
                self.last_heartbeat = datetime.now()
                self.heartbeat_count += 1
                
                # 每 10 次心跳记录一次日志（避免日志过多）
                if self.heartbeat_count % 10 == 0:
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


# 全局心跳监控器实例
_heartbeat_monitor: Optional[HeartbeatMonitor] = None


def get_heartbeat_monitor(interval: int = 30) -> HeartbeatMonitor:
    """获取全局心跳监控器实例"""
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor(interval=interval)
    return _heartbeat_monitor

