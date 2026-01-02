"""调试输出工具"""
import logging
from typing import Optional, Any, Dict
from rich.console import Console
from rich.panel import Panel
from shared.config import Config

config = Config()
console = Console()
logger = logging.getLogger(__name__)

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

