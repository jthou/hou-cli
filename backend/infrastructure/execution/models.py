"""代码执行数据模型"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class ExecutionRequest:
    """执行请求"""
    code: str
    language: str
    timeout: int = 30
    memory_limit_mb: Optional[int] = None
    cpu_limit: Optional[float] = None
    working_dir: Optional[str] = None
    explanation: Optional[str] = None


@dataclass
class ResourceUsage:
    """资源使用情况"""
    memory_used_mb: float = 0.0
    cpu_used_percent: float = 0.0
    execution_time_seconds: float = 0.0


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    resource_usage: Optional[ResourceUsage] = None
    language: str = ""
    code: str = ""
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

