"""流式数据格式化模块 - 负责将数据格式化为 SSE (Server-Sent Events) 格式"""
import json
import asyncio
import os
from typing import AsyncIterator, Optional, Callable, Any, Dict, Literal
import logging

logger = logging.getLogger(__name__)


def resolve_orchestration_trace_verbosity(context: Optional[Dict[str, Any]]) -> Literal["off", "summary", "full"]:
    # 时间：2026-03-13；理由：编排可观测性默认关，避免扰动 UX；方法：context 优先于 ORCH_TRACE_VERBOSITY 环境变量（见 docs/design/01-orchestrator-intent-driven-refactor-design.md §2.4.1）。
    ctx = context or {}
    raw = ctx.get("orchestration_trace")
    if raw is None:
        raw = ctx.get("trace_verbosity")
    if isinstance(raw, str):
        r = raw.lower().strip()
        if r in ("off", "none", "false", "0", ""):
            return "off"
        if r == "full":
            return "full"
        if r in ("summary", "on", "true", "1"):
            return "summary"
    env = (os.getenv("ORCH_TRACE_VERBOSITY") or "off").lower().strip()
    if env == "full":
        return "full"
    if env in ("summary", "on", "true", "1"):
        return "summary"
    return "off"


# 时间：2026-04-04；理由：思考链 __REASONING__ 等帧需透传前端但不得写入会话 assistant 正文；方法与前端 shouldAppendStreamingPlainText 对齐
_STREAM_ASSISTANT_PERSIST_EXCLUDE_PREFIXES: tuple[str, ...] = (
    "__DEBUG__:",
    "__TOOL__:",
    "__STATUS__:",
    "__REASONING__:",
    "__CTX_META__:",
    "__EVALUATION__:",
    "__ORCH_TRACE__:",
    "__PROGRESS__:",
    "__CONFIRM__:",
)


def should_persist_stream_chunk_in_assistant_message(chunk: str) -> bool:
    """流式块是否应拼入持久化的助手消息正文（False = 仍 yield 给前端）。"""
    if chunk is None:
        return False
    s = str(chunk)
    if not s:
        return False
    return not any(s.startswith(p) for p in _STREAM_ASSISTANT_PERSIST_EXCLUDE_PREFIXES)


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

    @staticmethod
    def build_orchestration_trace(envelope: dict) -> str:
        """编排追踪帧（用户向，与 __DEBUG__ 区分）。信封字段见 docs/design/01-orchestrator-intent-driven-refactor-design.md §2.4.2。"""
        return f"__ORCH_TRACE__:{json.dumps(envelope, ensure_ascii=False)}\n"

    @staticmethod
    def build_ctx_meta(meta: dict) -> str:
        # 时间：2026-03-13；理由：前端展示「本次选中的历史上下文」，非模型 CoT；方法与 __TOOL__ 并列由前端单独解析
        return f"__CTX_META__:{json.dumps(meta, ensure_ascii=False)}\n"


class SSEFormatter:
    """SSE (Server-Sent Events) 格式化器，负责将数据格式化为 SSE 格式"""
    
    @staticmethod
    def format_chunk(content: str, status: str = "streaming") -> str:
        """
        格式化一个数据块（SSE 格式）
        
        Args:
            content: 内容
            status: 状态（streaming/done/error）
            
        Returns:
            SSE 格式的字符串
        """
        return f"data: {json.dumps({'content': content, 'status': status}, ensure_ascii=False)}\n\n"
    
    @staticmethod
    def format_debug(debug_data: dict) -> str:
        """
        格式化调试信息
        
        Args:
            debug_data: 调试数据字典
            
        Returns:
            格式化的调试信息字符串
        """
        return f"__DEBUG__:{json.dumps(debug_data, ensure_ascii=False)}\n"
    
    @staticmethod
    def format_tool(tool_data: dict) -> str:
        """
        格式化工具调用信息
        
        Args:
            tool_data: 工具数据字典
            
        Returns:
            格式化的工具信息字符串
        """
        return f"__TOOL__:{json.dumps(tool_data, ensure_ascii=False)}\n"
    
    @staticmethod
    def format_confirm(confirm_data: dict) -> str:
        """
        格式化确认请求
        
        Args:
            confirm_data: 确认数据字典
            
        Returns:
            格式化的确认请求字符串
        """
        return f"__CONFIRM__:{json.dumps(confirm_data, ensure_ascii=False)}\n"
    
    @staticmethod
    def format_evaluation(evaluation_data: dict) -> str:
        """
        格式化评估结果
        
        Args:
            evaluation_data: 评估数据字典
            
        Returns:
            格式化的评估结果字符串
        """
        return f"__EVALUATION__:{json.dumps(evaluation_data, ensure_ascii=False)}\n"
    
    @staticmethod
    def format_status(status_data: dict) -> str:
        """
        格式化状态更新（用于长任务）
        
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
    def format_done() -> str:
        """格式化完成信号"""
        return SSEFormatter.format_chunk("", "done")
    
    @staticmethod
    def format_error(error: str) -> str:
        """格式化错误信号"""
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
                
                status_str = SSEFormatter.format_status(status_data)
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

