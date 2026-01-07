"""代码执行工具实现"""
import asyncio
from typing import Dict, Any, Optional, TYPE_CHECKING
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.infrastructure.execution import SecureExecutor, ExecutionRequest
from backend.infrastructure.execution.risk_detector import RiskDetector, RiskLevel

if TYPE_CHECKING:
    from backend.infrastructure.execution.interactive_executor import InteractiveExecutor

try:
    from backend.infrastructure.execution.interactive_executor import InteractiveExecutor as _InteractiveExecutor
    INTERACTIVE_AVAILABLE = True
except ImportError:
    INTERACTIVE_AVAILABLE = False
    _InteractiveExecutor = None


class CodeExecutorTool(Tool):
    """代码执行工具
    
    允许 AI 助手在安全的沙盒环境中执行脚本代码。
    支持 Python、bash、zsh、PowerShell、batch 等脚本语言。
    """
    
    def __init__(self):
        """初始化代码执行工具"""
        parameters = [
            ToolParameter(
                name="code",
                type="string",
                description="要执行的代码内容",
                required=True
            ),
            ToolParameter(
                name="language",
                type="string",
                description="代码语言：python, bash, zsh, powershell, batch",
                required=True,
                enum=["python", "bash", "zsh", "powershell", "batch"]
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="执行超时时间（秒），默认 30，最大 300",
                required=False,
                default=30
            ),
            ToolParameter(
                name="explanation",
                type="string",
                description="代码说明（可选），用于记录执行目的",
                required=False
            )
        ]
        
        super().__init__(
            name="execute_code",
            description=(
                "在安全的沙盒环境中执行脚本代码。"
                "\n支持的语言："
                "- python: Python 脚本（跨平台）"
                "- bash: Bash 脚本（Linux/macOS）"
                "- zsh: Zsh 脚本（macOS）"
                "- powershell: PowerShell 脚本（Windows/跨平台）"
                "- batch: Batch 脚本（Windows）"
                "\n核心原则（非常重要）："
                "- 严格按照用户指令执行，不要添加额外的探索、检查或推理"
                "- 用户要求执行什么命令，就执行什么命令，不要自作主张添加其他操作"
                "- 例如：用户要求 '显示 /home 下的所有文件'，直接执行 'ls /home'，不要去找 /dev、/Users 等其他路径"
                "- 优先使用简单、直接的命令，避免不必要的复杂性"
                "- 能用单条命令解决的问题，不要写多行代码"
                "- 不要过度思考，不要添加用户没有要求的额外功能"
                "\n安全限制："
                "- 代码在隔离环境中执行"
                "- 资源限制：CPU、内存、时间"
                "- 禁止访问敏感目录和危险命令"
                "\n使用场景："
                "- 数据处理和分析"
                "- 文件操作和系统管理"
                "- 数据验证和转换"
                "- 自动化任务"
                "\n注意："
                "- 仅支持脚本语言，不支持编译型语言"
                "- 代码长度限制：10KB"
                "- 输出大小限制：10MB"
            ),
            parameters=parameters
        )
        
        self.executor = SecureExecutor()
        self.risk_detector = RiskDetector()
        self.interactive_executor: Optional[Any] = None
        if INTERACTIVE_AVAILABLE and _InteractiveExecutor is not None:
            try:
                self.interactive_executor = _InteractiveExecutor()
            except Exception:
                self.interactive_executor = None  # pexpect 未安装或初始化失败
    
    def execute(self, **kwargs) -> ToolResult:
        """执行代码（同步包装异步方法）"""
        # 由于 Tool.execute 是同步的，我们需要使用 asyncio.run
        # 但要注意如果已经在事件循环中，需要使用其他方法
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用线程池执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._execute_async(**kwargs))
                return future.result(timeout=kwargs.get("timeout", 30) + 5)  # 超时时间+5秒缓冲
        except RuntimeError:
            # 没有运行中的事件循环，直接创建新的
            return asyncio.run(self._execute_async(**kwargs))
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行代码"""
        code = kwargs.get("code")
        language = kwargs.get("language")
        timeout = kwargs.get("timeout", 30)
        explanation = kwargs.get("explanation", "")
        
        if not code:
            return ToolResult(
                success=False,
                error="Code parameter is required"
            )
        
        if not language:
            return ToolResult(
                success=False,
                error="Language parameter is required"
            )
        
        # 验证超时时间
        if timeout < 1 or timeout > 300:
            timeout = 30
        
        # 检测风险
        risk_level, reason = self.risk_detector.detect_risk(code, language)
        
        # 如果是严重风险，直接拒绝
        if not self.risk_detector.is_allowed(risk_level):
            return ToolResult(
                success=False,
                error=f"禁止执行：{reason}",
                data={
                    "risk_level": risk_level.value,
                    "reason": reason,
                    "requires_confirmation": False,
                    "language": language,
                    "code": code
                }
            )
        
        # 如果需要确认，返回特殊状态（由 Orchestrator 处理确认流程）
        if self.risk_detector.requires_confirmation(risk_level):
            return ToolResult(
                success=False,
                error="需要用户确认",
                data={
                    "risk_level": risk_level.value,
                    "reason": reason,
                    "requires_confirmation": True,
                    "requires_password": self.risk_detector.requires_password(risk_level),
                    "language": language,
                    "code": code,
                    "explanation": explanation
                }
            )
        
        try:
            # 检测是否需要交互式输入
            use_interactive = False
            if self.interactive_executor is not None:
                use_interactive = self.interactive_executor.detect_interactive_input(code, language)
            
            if use_interactive and self.interactive_executor is not None:
                # 使用交互式执行器
                # 注意：交互式执行需要输入处理函数，这里暂时使用占位符
                # 实际实现需要前后端配合
                def input_handler(prompt: str, is_password: bool) -> str:
                    # TODO: 实现输入处理，需要与前端交互
                    # 暂时返回空字符串
                    return ""
                
                result = await self.interactive_executor.execute_interactive(
                    code=code,
                    language=language,
                    timeout=timeout,
                    input_handler=input_handler
                )
            else:
                # 使用普通执行器
                request = ExecutionRequest(
                    code=code,
                    language=language,
                    timeout=timeout,
                    explanation=explanation
                )
                
                # 执行代码
                result = await self.executor.execute_code_safely(request)
            
            # 构建返回结果
            return ToolResult(
                success=result.success,
                data={
                    "output": result.output,
                    "error": result.error,
                    "exit_code": result.exit_code,
                    "execution_time": result.resource_usage.execution_time_seconds if result.resource_usage else 0,
                    "memory_used": result.resource_usage.memory_used_mb if result.resource_usage else 0,
                    "language": language,
                    "explanation": explanation
                },
                error=result.error if not result.success else None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"代码执行失败: {str(e)}"
            )

