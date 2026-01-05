"""代码执行工具实现"""
import asyncio
from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.infrastructure.execution import SecureExecutor, ExecutionRequest


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
        
        try:
            # 创建执行请求
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

