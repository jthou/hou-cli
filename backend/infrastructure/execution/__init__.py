"""代码执行模块"""
from backend.infrastructure.execution.models import (
    ExecutionRequest,
    ExecutionResult,
    ResourceUsage
)
from backend.infrastructure.execution.executor import SubprocessExecutor
from backend.infrastructure.execution.secure_executor import SecureExecutor
from backend.infrastructure.execution.result_handler import ResultHandler
from backend.infrastructure.execution.auto_executor import (
    CodeExtractor,
    AutoCodeExecutor
)
from backend.infrastructure.execution.risk_detector import (
    RiskLevel,
    RiskDetector
)

try:
    from backend.infrastructure.execution.interactive_executor import InteractiveExecutor
    __all__ = [
        "ExecutionRequest",
        "ExecutionResult",
        "ResourceUsage",
        "SubprocessExecutor",
        "SecureExecutor",
        "ResultHandler",
        "CodeExtractor",
        "AutoCodeExecutor",
        "RiskLevel",
        "RiskDetector",
        "InteractiveExecutor",
    ]
except ImportError:
    __all__ = [
        "ExecutionRequest",
        "ExecutionResult",
        "ResourceUsage",
        "SubprocessExecutor",
        "SecureExecutor",
        "ResultHandler",
        "CodeExtractor",
        "AutoCodeExecutor",
        "RiskLevel",
        "RiskDetector",
    ]
