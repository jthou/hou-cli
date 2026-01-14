"""流式发送模块 - 负责向后端发送流式数据"""
import json
import asyncio
from typing import AsyncIterator, Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


class StreamMessageBuilder:
    """流式消息构建器（同步版本，用于异步生成器）"""
    
    @staticmethod
    def build_debug(debug_data: dict) -> str:
        """构建调试信息消息"""
        return f"__DEBUG__:{json.dumps(debug_data, ensure_ascii=False)}\n"
    
    @staticmethod
    def build_tool(tool_data: dict) -> str:
        """构建工具调用消息"""
        return f"__TOOL__:{json.dumps(tool_data, ensure_ascii=False)}\n"
    
    @staticmethod
    def build_confirm(confirm_data: dict) -> str:
        """构建确认请求消息"""
        return f"__CONFIRM__:{json.dumps(confirm_data, ensure_ascii=False)}\n"
    
    @staticmethod
    def build_evaluation(evaluation_data: dict) -> str:
        """构建评估结果消息"""
        return f"__EVALUATION__:{json.dumps(evaluation_data, ensure_ascii=False)}\n"
    
    @staticmethod
    def build_status(status_data: dict) -> str:
        """构建状态更新消息"""
        return f"__STATUS__:{json.dumps(status_data, ensure_ascii=False)}\n"


class StreamSender:
    """流式数据发送器，负责将数据以 SSE 格式发送到前端"""
    
    @staticmethod
    async def send_chunk(content: str, status: str = "streaming") -> str:
        """
        发送一个数据块（SSE 格式）
        
        Args:
            content: 内容
            status: 状态（streaming/done/error）
            
        Returns:
            SSE 格式的字符串
        """
        return f"data: {json.dumps({'content': content, 'status': status}, ensure_ascii=False)}\n\n"
    
    @staticmethod
    async def send_debug(debug_data: dict) -> str:
        """
        发送调试信息
        
        Args:
            debug_data: 调试数据字典
            
        Returns:
            格式化的调试信息字符串
        """
        return f"__DEBUG__:{json.dumps(debug_data, ensure_ascii=False)}\n"
    
    @staticmethod
    async def send_tool(tool_data: dict) -> str:
        """
        发送工具调用信息
        
        Args:
            tool_data: 工具数据字典
            
        Returns:
            格式化的工具信息字符串
        """
        return f"__TOOL__:{json.dumps(tool_data, ensure_ascii=False)}\n"
    
    @staticmethod
    async def send_confirm(confirm_data: dict) -> str:
        """
        发送确认请求
        
        Args:
            confirm_data: 确认数据字典
            
        Returns:
            格式化的确认请求字符串
        """
        return f"__CONFIRM__:{json.dumps(confirm_data, ensure_ascii=False)}\n"
    
    @staticmethod
    async def send_evaluation(evaluation_data: dict) -> str:
        """
        发送评估结果
        
        Args:
            evaluation_data: 评估数据字典
            
        Returns:
            格式化的评估结果字符串
        """
        return f"__EVALUATION__:{json.dumps(evaluation_data, ensure_ascii=False)}\n"
    
    @staticmethod
    async def send_status(status_data: dict) -> str:
        """
        发送状态更新（用于长任务）
        
        Args:
            status_data: 状态数据字典，包含：
                - task: 任务名称
                - progress: 进度（0-100）
                - message: 状态消息
                - elapsed_time: 已用时间（秒）
                - estimated_remaining: 预计剩余时间（秒，可选）
                
        Returns:
            格式化的状态更新字符串
        """
        return f"__STATUS__:{json.dumps(status_data, ensure_ascii=False)}\n"
    
    @staticmethod
    async def send_done() -> str:
        """发送完成信号"""
        return await StreamSender.send_chunk("", "done")
    
    @staticmethod
    async def send_error(error: str) -> str:
        """发送错误信号"""
        return f"data: {json.dumps({'content': '', 'status': 'error', 'error': error}, ensure_ascii=False)}\n\n"


class LongTaskMonitor:
    """长任务监控器，用于在长任务执行期间定时发送状态更新"""
    
    def __init__(
        self,
        send_func: Callable[[str], Any],
        task_name: str,
        update_interval: float = 5.0
    ):
        """
        初始化长任务监控器
        
        Args:
            send_func: 发送函数，接受字符串参数
            task_name: 任务名称
            update_interval: 状态更新间隔（秒）
        """
        self.send_func = send_func
        self.task_name = task_name
        self.update_interval = update_interval
        self.start_time: Optional[float] = None
        self.last_update_time: Optional[float] = None
        self.monitor_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.current_progress = 0
        self.current_message = ""
    
    async def start(self):
        """启动监控"""
        import time
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """停止监控"""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
    
    def update_progress(self, progress: int, message: str = ""):
        """
        更新进度
        
        Args:
            progress: 进度（0-100）
            message: 状态消息
        """
        self.current_progress = max(0, min(100, progress))
        self.current_message = message
    
    async def _monitor_loop(self):
        """监控循环，定时发送状态更新"""
        import time
        try:
            while self.is_running:
                await asyncio.sleep(self.update_interval)
                
                if not self.is_running:
                    break
                
                elapsed_time = time.time() - self.start_time if self.start_time else 0
                
                status_data = {
                    "task": self.task_name,
                    "progress": self.current_progress,
                    "message": self.current_message or "处理中...",
                    "elapsed_time": round(elapsed_time, 2)
                }
                
                # 如果进度大于0，可以估算剩余时间
                if self.current_progress > 0:
                    estimated_total = elapsed_time / (self.current_progress / 100)
                    estimated_remaining = max(0, estimated_total - elapsed_time)
                    status_data["estimated_remaining"] = round(estimated_remaining, 2)
                
                status_str = await StreamSender.send_status(status_data)
                try:
                    await self.send_func(status_str)
                except Exception as e:
                    logger.warning(f"发送状态更新失败: {str(e)}")
                    # 如果发送失败，停止监控
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"监控循环异常: {str(e)}", exc_info=True)

