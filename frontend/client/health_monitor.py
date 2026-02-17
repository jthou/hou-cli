"""前端健康监控模块"""
import asyncio
import logging
import time
from typing import Optional, Callable
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class HealthMonitor:
    """健康监控器（前端）"""
    
    def __init__(
        self,
        base_url: str,
        interval: int = 30,
        timeout: float = 5.0,
        max_failures: int = 3
    ):
        """
        初始化健康监控器
        
        Args:
            base_url: 后端服务 URL
            interval: 检查间隔（秒），默认 30 秒
            timeout: 请求超时（秒），默认 5 秒
            max_failures: 最大连续失败次数，超过后触发回调
        """
        self.base_url = base_url
        self.interval = interval
        self.timeout = timeout
        self.max_failures = max_failures
        
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.last_check: Optional[datetime] = None
        self.last_success: Optional[datetime] = None
        self.consecutive_failures = 0
        self.total_checks = 0
        self.total_failures = 0
        
        # 回调函数
        self.on_unhealthy: Optional[Callable] = None
        self.on_recovered: Optional[Callable] = None
    
    def set_callbacks(
        self,
        on_unhealthy: Optional[Callable] = None,
        on_recovered: Optional[Callable] = None
    ):
        """
        设置回调函数
        
        Args:
            on_unhealthy: 后端不健康时的回调
            on_recovered: 后端恢复时的回调
        """
        self.on_unhealthy = on_unhealthy
        self.on_recovered = on_recovered
    
    async def start(self):
        """启动健康监控"""
        if self.is_running:
            logger.warning("健康监控已在运行")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info(f"健康监控已启动，检查间隔: {self.interval} 秒")
    
    async def stop(self):
        """停止健康监控"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("健康监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        was_healthy = True
        
        while self.is_running:
            try:
                is_healthy = await self._check_health()
                self.last_check = datetime.now()
                self.total_checks += 1
                
                if is_healthy:
                    self.last_success = datetime.now()
                    if self.consecutive_failures > 0:
                        self.consecutive_failures = 0
                        if not was_healthy and self.on_recovered:
                            try:
                                await self.on_recovered()
                            except Exception as e:
                                logger.error(f"恢复回调执行失败: {e}")
                        was_healthy = True
                        logger.info("后端服务已恢复")
                else:
                    self.consecutive_failures += 1
                    self.total_failures += 1
                    
                    if self.consecutive_failures >= self.max_failures:
                        if was_healthy and self.on_unhealthy:
                            try:
                                await self.on_unhealthy()
                            except Exception as e:
                                logger.error(f"不健康回调执行失败: {e}")
                        was_healthy = False
                        logger.warning(
                            f"后端服务不健康，连续失败 {self.consecutive_failures} 次"
                        )
                
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康监控错误: {e}", exc_info=True)
                await asyncio.sleep(self.interval)
    
    async def _check_health(self) -> bool:
        """检查后端健康状态"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"健康检查失败: {e}")
            return False
    
    def get_status(self) -> dict:
        """获取监控状态"""
        return {
            "is_running": self.is_running,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "consecutive_failures": self.consecutive_failures,
            "total_checks": self.total_checks,
            "total_failures": self.total_failures,
            "success_rate": (
                (self.total_checks - self.total_failures) / self.total_checks * 100
                if self.total_checks > 0 else 0
            ),
            "is_healthy": self.consecutive_failures < self.max_failures,
        }
    
    def is_healthy(self) -> bool:
        """检查当前是否健康"""
        return self.consecutive_failures < self.max_failures

