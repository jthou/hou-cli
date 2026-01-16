"""调试输出工具"""
import os
import json
import logging
from typing import Optional, Any, Dict
from rich.console import Console
from rich.panel import Panel
from shared.config import Config

config = Config()
console = Console()
logger = logging.getLogger(__name__)


def get_debug_log_path() -> Optional[str]:
    """获取调试日志文件路径（从环境变量读取）"""
    debug_log_path = os.getenv("DEBUG_LOG_PATH")
    if debug_log_path:
        return debug_log_path
    # 如果环境变量未设置，返回 None（不记录日志）
    return None


def debug_log(
    message: str,
    location: Optional[str] = None,
    level: str = "debug",
    data: Optional[dict] = None,
    hypothesis_id: str = "A",
    logger_name: Optional[str] = None
):
    """统一的调试日志接口
    
    同时支持：
    - 标准 Python logging（debug/info/warning/error）
    - 文件日志（如果设置了 DEBUG_LOG_PATH）
    
    自动获取调用位置信息（类似 C 的 __FILE__, __FUNCTION__, __LINE__）：
    - 如果 location 未提供，自动从调用栈获取文件名、函数名和行号
    
    Args:
        message: 日志消息
        location: 日志位置（如 "routes.py:chat_stream:entry"），可选，不提供则自动获取
        level: 日志级别（debug/info/warning/error），默认 "debug"
        data: 附加数据字典（可选）
        hypothesis_id: 假设ID（默认 "A"），仅用于文件日志
        logger_name: logger 名称，None 时使用调用者的模块名
    """
    import inspect
    from pathlib import Path
    
    # 自动获取调用位置信息（类似 C 的 __FILE__, __FUNCTION__, __LINE__）
    # 注意：获取的是调用 debug_log() 的位置，不是 debug_log 函数自身的位置
    if location is None:
        frame = inspect.currentframe()
        # frame 是 debug_log 函数自己的帧
        # frame.f_back 是调用 debug_log() 的位置（调用者）
        if frame and frame.f_back:
            caller_frame = frame.f_back  # 获取调用者的帧
            # 获取文件名（只取文件名，不包含路径）
            file_path = caller_frame.f_code.co_filename
            file_name = Path(file_path).name
            # 获取函数名（调用 debug_log 的函数名）
            function_name = caller_frame.f_code.co_name
            # 获取行号（调用 debug_log 的行号）
            line_number = caller_frame.f_lineno
            # 构建 location 字符串
            location = f"{file_name}:{function_name}:{line_number}"
        else:
            location = "unknown"
    
    # 1. 输出到标准 logging
    if logger_name:
        log = logging.getLogger(logger_name)
    else:
        # 自动获取调用者的模块名
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_module = frame.f_back.f_globals.get('__name__', __name__)
            log = logging.getLogger(caller_module)
        else:
            log = logger
    
    # 格式化消息
    full_message = f"[{location}] {message}"
    
    # 如果有附加数据，添加到消息中
    if data:
        data_str = ", ".join([f"{k}={v}" for k, v in data.items()])
        full_message = f"{full_message} | {data_str}"
    
    # 根据级别输出
    if level == "debug":
        log.debug(full_message)
    elif level == "info":
        log.info(full_message)
    elif level == "warning":
        log.warning(full_message)
    elif level == "error":
        log.error(full_message)
    
    # 2. 写入文件日志（如果设置了 DEBUG_LOG_PATH）
    debug_log_path = get_debug_log_path()
    if debug_log_path:
        try:
            import time
            log_entry = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "level": level,
                "data": data or {},
                "timestamp": int(time.time() * 1000)
            }
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                f.flush()
        except Exception as log_err:
            log.error(f"文件日志写入失败: {log_err}")


def write_debug_log(
    location: str,
    message: str,
    hypothesis_id: str = "A",
    data: Optional[dict] = None,
    log_error: bool = True
):
    """写入调试日志（已废弃，请使用 debug_log）
    
    为了向后兼容保留，内部调用 debug_log
    """
    debug_log(
        message=message,
        location=location,
        level="debug",
        data=data,
        hypothesis_id=hypothesis_id
    )

class DebugOutput:
    """调试输出类"""
    
    def __init__(self, enabled: Optional[bool] = None):
        """
        初始化调试输出
        
        Args:
            enabled: 是否启用调试输出，None 时使用配置
        """
        self.enabled = enabled if enabled is not None else config.is_development
    
    def log(self, message: str, level: str = "info"):
        """输出调试日志"""
        if not self.enabled:
            return
        
        # 使用 logger 记录
        if level == "debug":
            logger.debug(message)
        elif level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        
        # 使用 Rich 输出到控制台（开发环境）
        if config.is_development:
            style = {
                "debug": "dim cyan",
                "info": "dim blue",
                "warning": "yellow",
                "error": "red"
            }.get(level, "dim")
            console.print(f"[{style}][DEBUG][/{style}] {message}")
    
    def log_orchestrator_step(self, step: str, details: Optional[Dict] = None):
        """输出 Orchestrator 处理步骤"""
        if not self.enabled:
            return
        
        message = f"Orchestrator: {step}"
        if details:
            detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message += f" ({detail_str})"
        
        self.log(message, level="debug")
    
    def log_context_operation(self, operation: str, session_id: str, details: Optional[Dict] = None):
        """输出上下文操作"""
        if not self.enabled:
            return
        
        # 截断 session_id 用于显示
        session_preview = session_id[:8] + "..." if len(session_id) > 8 else session_id
        message = f"ContextManager: {operation} (session_id={session_preview})"
        if details:
            detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message += f" ({detail_str})"
        
        self.log(message, level="debug")
    
    def log_llm_request(self, system_prompt: str, user_prompt: str, model: str):
        """输出 LLM 请求信息"""
        if not self.enabled:
            return
        
        # 截断长文本用于显示
        system_preview = system_prompt[:50] + "..." if len(system_prompt) > 50 else system_prompt
        user_preview = user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt
        
        self.log(f"LLM Request: model={model}", level="debug")
        self.log(f"  System: {system_preview}", level="debug")
        self.log(f"  User: {user_preview}", level="debug")
    
    def log_llm_response(self, response: str, model: str):
        """输出 LLM 响应信息"""
        if not self.enabled:
            return
        
        preview = response[:100] + "..." if len(response) > 100 else response
        self.log(f"LLM Response: model={model}, length={len(response)}", level="debug")
        self.log(f"  Preview: {preview}", level="debug")
    
    def log_llm_thinking(self, thinking: str):
        """输出 LLM 思考过程（如果支持）"""
        if not self.enabled:
            return
        
        # 使用 Panel 显示思考过程
        console.print(Panel(
            thinking,
            border_style="dim cyan",
            title="[dim cyan]🤔 模型思考过程[/dim cyan]",
            padding=(1, 2)
        ))

