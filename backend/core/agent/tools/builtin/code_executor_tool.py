"""代码执行工具实现

将 execute_code 拆分为 exec_py（Python）和 exec_shell（shell/zsh），
便于 LLM 根据任务类型选择对应工具。
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.infrastructure.execution import SecureExecutor, ExecutionRequest
from backend.infrastructure.execution.risk_detector import RiskDetector, RiskLevel
from backend.infrastructure.execution.allowlist import get_allowlist_evaluator
from backend.infrastructure.execution.approval import get_approval_manager

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

if TYPE_CHECKING:
    from backend.infrastructure.execution.interactive_executor import InteractiveExecutor

try:
    from backend.infrastructure.execution.interactive_executor import InteractiveExecutor as _InteractiveExecutor
    INTERACTIVE_AVAILABLE = True
except ImportError:
    INTERACTIVE_AVAILABLE = False
    _InteractiveExecutor = None


def _build_safety_descriptions() -> tuple[str, str]:
    """构建危险命令和受限路径描述"""
    executor = SecureExecutor()
    dangerous_commands = executor.COMMAND_BLACKLIST
    restricted_paths = executor.RESTRICTED_PATHS

    file_delete_cmds = [cmd for cmd in dangerous_commands if cmd in ["rm", "del"]]
    permission_cmds = [cmd for cmd in dangerous_commands if cmd in ["sudo", "su", "chmod", "chown", "chgrp"]]
    disk_cmds = [cmd for cmd in dangerous_commands if cmd in ["format", "mkfs", "fdisk", "dd"]]
    process_cmds = [cmd for cmd in dangerous_commands if cmd in ["killall", "pkill"]]

    dangerous_cmds_desc = ""
    if file_delete_cmds:
        dangerous_cmds_desc += f"- 文件删除：{', '.join(file_delete_cmds)}\n"
    if permission_cmds:
        dangerous_cmds_desc += f"- 权限管理：{', '.join(permission_cmds)}\n"
    if disk_cmds:
        dangerous_cmds_desc += f"- 磁盘操作：{', '.join(disk_cmds)}\n"
    if process_cmds:
        dangerous_cmds_desc += f"- 进程管理：{', '.join(process_cmds)}\n"

    restricted_paths_desc = ""
    linux_paths = [p for p in restricted_paths if not p.startswith("C:")]
    windows_paths = [p for p in restricted_paths if p.startswith("C:")]
    if linux_paths:
        restricted_paths_desc += f"- Linux/macOS: {', '.join(linux_paths)}\n"
    if windows_paths:
        restricted_paths_desc += f"- Windows: {', '.join(windows_paths)}\n"

    return dangerous_cmds_desc, restricted_paths_desc


class _BaseCodeExecutorTool(Tool):
    """代码执行工具基类

    子类需指定 name 和 language。
    """

    def __init__(self, name: str, language: str, description: str):
        dangerous_cmds_desc, restricted_paths_desc = _build_safety_descriptions()

        parameters = [
            ToolParameter(
                name="code",
                type="string",
                description="要执行的代码内容",
                required=True
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
            ),
            ToolParameter(
                name="approval_token",
                type="string",
                description="用户确认后获得的 token（需审批时由前端传入）",
                required=False
            ),
            ToolParameter(
                name="approval_id",
                type="string",
                description="待审批请求 ID（返回 requires_approval 时一并返回，供前端调用 approve API）",
                required=False
            )
        ]

        full_description = (
            f"{description}"
            "\n安全限制："
            "\n- 代码在隔离环境中执行"
            "\n- 资源限制：CPU、内存、时间"
            "\n- 代码长度限制：10KB"
            "\n- 输出大小限制：10MB"
            f"\n【重要】禁止使用的危险命令（会被拒绝执行）："
            f"\n{dangerous_cmds_desc}"
            "- 注意：这些命令即使作为字符串的一部分也会被检测到，请避免使用"
            f"\n【重要】禁止访问的敏感目录（会被拒绝执行）："
            f"\n{restricted_paths_desc}"
            "- 注意：代码中包含这些路径会被拒绝执行"
        )

        super().__init__(name=name, description=full_description, parameters=parameters)
        self._language = language
        self.executor = SecureExecutor()
        self.risk_detector = RiskDetector()
        self.allowlist_evaluator = get_allowlist_evaluator()
        self.approval_manager = get_approval_manager()
        self.interactive_executor: Optional[Any] = None
        if INTERACTIVE_AVAILABLE and _InteractiveExecutor is not None:
            try:
                self.interactive_executor = _InteractiveExecutor()
            except Exception:
                self.interactive_executor = None

    def execute(self, **kwargs) -> ToolResult:
        """执行代码（同步包装异步方法）"""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._execute_async(**kwargs))
                return future.result(timeout=kwargs.get("timeout", 30) + 5)
        except RuntimeError:
            return asyncio.run(self._execute_async(**kwargs))

    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行代码"""
        code = kwargs.get("code")
        timeout = kwargs.get("timeout", 30)
        explanation = kwargs.get("explanation", "")
        approval_token = kwargs.get("approval_token", "")
        language = self._language

        if not code:
            return ToolResult(success=False, error="Code parameter is required")

        if timeout < 1 or timeout > 300:
            timeout = 30

        # 1. 若有 approval_token，校验后直接执行
        if approval_token:
            pending = self.approval_manager.verify_token(approval_token)
            if not pending:
                return ToolResult(
                    success=False,
                    error="审批 token 无效或已过期，请重新发起执行并确认",
                    data={"requires_approval": False}
                )
            if pending.code and pending.code.strip() != code.strip():
                return ToolResult(
                    success=False,
                    error="审批 token 与当前代码不一致，请重新发起执行并确认",
                    data={"requires_approval": False}
                )
            return await self._do_execute(
                code, language, timeout, explanation,
                skip_blacklist_check=True,
                skip_path_check=True
            )

        # 2. 代码助手场景：始终需用户确认
        if kwargs.get("_require_approval_always"):
            pending = self.approval_manager.create_pending(
                command=code.split("\n")[0] if code else "",
                workdir="",
                language=language,
                risk_level=RiskLevel.SAFE.value,
                reason="代码助手执行前需用户确认",
                code=code,
                tool_name=self.name
            )
            return ToolResult(
                success=False,
                error="需要用户确认",
                data={
                    "risk_level": RiskLevel.SAFE.value,
                    "reason": "代码助手执行前需用户确认",
                    "requires_confirmation": True,
                    "requires_password": False,
                    "approval_id": pending.id,
                    "language": language,
                    "code": code,
                    "explanation": explanation,
                    "preview": {"command": code[:200], "risk_level": RiskLevel.SAFE.value}
                }
            )

        # 3. Allowlist：命中则免审直接执行（仅 zsh）
        if language.lower() in ("zsh", "shell", "sh", "bash"):
            allow_result = self.allowlist_evaluator.evaluate(code, workdir="", language=language)
            if allow_result.satisfied:
                return await self._do_execute(code, language, timeout, explanation)

        # 4. 风险检测
        risk_level, reason = self.risk_detector.detect_risk(code, language)

        # 5. 严重风险直接拒绝
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

        # 6. 需确认：创建待审批，返回 approval_id
        if self.risk_detector.requires_confirmation(risk_level):
            pending = self.approval_manager.create_pending(
                command=code.split("\n")[0] if code else "",
                workdir="",
                language=language,
                risk_level=risk_level.value,
                reason=reason,
                code=code,
                tool_name=self.name
            )
            return ToolResult(
                success=False,
                error="需要用户确认",
                data={
                    "risk_level": risk_level.value,
                    "reason": reason,
                    "requires_confirmation": True,
                    "requires_password": self.risk_detector.requires_password(risk_level),
                    "approval_id": pending.id,
                    "language": language,
                    "code": code,
                    "explanation": explanation,
                    "preview": {"command": code[:200], "risk_level": risk_level.value}
                }
            )

        # 7. 安全级别，直接执行
        return await self._do_execute(code, language, timeout, explanation)

    async def _do_execute(
        self,
        code: str,
        language: str,
        timeout: int,
        explanation: str,
        skip_blacklist_check: bool = False,
        skip_path_check: bool = False
    ) -> ToolResult:
        """实际执行代码"""
        try:
            use_interactive = False
            if self.interactive_executor is not None:
                use_interactive = self.interactive_executor.detect_interactive_input(code, language)

            if use_interactive and self.interactive_executor is not None:
                def input_handler(prompt: str, is_password: bool) -> str:
                    return ""

                result = await self.interactive_executor.execute_interactive(
                    code=code,
                    language=language,
                    timeout=timeout,
                    input_handler=input_handler
                )
            else:
                request = ExecutionRequest(
                    code=code,
                    language=language,
                    timeout=timeout,
                    explanation=explanation
                )
                on_stdout = lambda line: self.report_progress(line) if line else None
                on_stderr = lambda line: self.report_progress(line) if line else None
                result = await self.executor.execute_code_safely(
                    request,
                    skip_blacklist_check=skip_blacklist_check,
                    skip_path_check=skip_path_check,
                    on_stdout=on_stdout,
                    on_stderr=on_stderr
                )

            def safe_clean_text(text: str) -> str:
                if not text:
                    return ""
                try:
                    return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                except Exception:
                    return str(text).encode('utf-8', errors='replace').decode('utf-8', errors='replace')

            return ToolResult(
                success=result.success,
                data={
                    "output": safe_clean_text(result.output),
                    "error": safe_clean_text(result.error),
                    "exit_code": result.exit_code,
                    "execution_time": result.resource_usage.execution_time_seconds if result.resource_usage else 0,
                    "memory_used": result.resource_usage.memory_used_mb if result.resource_usage else 0,
                    "language": language,
                    "explanation": explanation
                },
                error=safe_clean_text(result.error) if not result.success else None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"代码执行失败: {str(e)}"
            )


class ExecPyTool(_BaseCodeExecutorTool):
    """执行 Python 代码"""

    def __init__(self):
        desc = (
            "在安全的沙盒环境中执行 Python 脚本（每次独立执行，不保留状态）。"
            "\n【使用场景】"
            "\n- 读取文件、处理数据、输出结果"
            "\n- 数据分析、格式转换、简单计算"
            "\n- 一次性 Python 脚本任务"
            "\n核心原则：严格按照用户指令执行，不要添加额外的探索或推理。"
        )
        super().__init__(
            name="exec_py",
            language="python",
            description=desc
        )


class ExecShellTool(_BaseCodeExecutorTool):
    """执行 Shell/Zsh 代码"""

    def __init__(self):
        desc = (
            "在安全的沙盒环境中执行 Shell/Zsh 脚本（每次独立执行，不保留状态）。"
            "\n【使用场景】"
            "\n- 文件操作（ls、cat、cp、mv 等）"
            "\n- 系统命令、环境检查"
            "\n- 一次性 shell 脚本任务"
            "\n核心原则：严格按照用户指令执行，不要自作主张添加其他操作。"
            "\n例如：用户要求 '显示 /home 下的所有文件'，直接执行 'ls /home'。"
        )
        super().__init__(
            name="exec_shell",
            language="zsh",
            description=desc
        )
