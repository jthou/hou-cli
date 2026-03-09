"""exec 工具：执行 shell 命令，支持后台、流式、超时"""
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.infrastructure.execution.obfuscation_detector import ObfuscationDetector
from backend.infrastructure.execution.preflight import validate_script_for_shell_bleed
from backend.infrastructure.execution.allowlist import get_allowlist_evaluator
from backend.infrastructure.execution.approval import get_approval_manager
from backend.infrastructure.execution.risk_detector import RiskDetector, RiskLevel
from backend.infrastructure.execution.run_exec import run_exec_process


class ExecTool(Tool):
    """exec 工具

    执行 shell 命令，支持后台、超时。
    使用 zsh 执行，支持 allowlist 免审、approval 审批。
    """

    def __init__(self):
        parameters = [
            ToolParameter(name="command", type="string", description="要执行的 shell 命令", required=True),
            ToolParameter(name="workdir", type="string", description="工作目录（可选）", required=False),
            ToolParameter(name="timeout", type="integer", description="超时秒数（默认 60）", required=False, default=60),
            ToolParameter(name="background", type="boolean", description="是否立即后台执行", required=False, default=False),
            ToolParameter(name="pty", type="boolean", description="使用 PTY（伪终端，支持彩色输出）", required=False, default=False),
            ToolParameter(name="approval_token", type="string", description="用户确认后的 token", required=False),
            ToolParameter(name="approval_id", type="string", description="待审批 ID", required=False),
        ]
        super().__init__(
            name="exec",
            description=(
                "执行 shell 命令（通过 zsh）。"
                "适用于：执行单条命令、后台任务、需指定工作目录的场景。"
                "与 execute_code 区别：exec 面向命令字符串，支持 background；execute_code 面向代码块、多语言。"
                "安全：危险命令需用户确认；命中 allowlist 可免审。"
            ),
            parameters=parameters
        )
        self.obfuscation_detector = ObfuscationDetector()
        self.allowlist_evaluator = get_allowlist_evaluator()
        self.approval_manager = get_approval_manager()
        self.risk_detector = RiskDetector()

    def execute(self, **kwargs) -> ToolResult:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as ex:
                return ex.submit(
                    asyncio.run,
                    self._execute_async(**kwargs)
                ).result(timeout=kwargs.get("timeout", 60) + 10)
        except RuntimeError:
            return asyncio.run(self._execute_async(**kwargs))

    async def _execute_async(self, **kwargs) -> ToolResult:
        command = kwargs.get("command", "").strip()
        workdir = kwargs.get("workdir", "") or "."
        timeout = kwargs.get("timeout", 60) or 60
        background = kwargs.get("background", False)
        use_pty = kwargs.get("pty", False)
        approval_token = kwargs.get("approval_token", "")

        if not command:
            return ToolResult(success=False, error="command 参数必需")

        if timeout < 1 or timeout > 3600:
            timeout = 60

        # 1. approval_token 校验
        if approval_token:
            pending = self.approval_manager.verify_token(approval_token)
            if not pending:
                return ToolResult(success=False, error="审批 token 无效或已过期")
            if pending.command and pending.command.strip() != command.strip():
                return ToolResult(success=False, error="审批 token 与当前命令不一致")
            return await self._do_execute(command, workdir, timeout, background, use_pty)

        # 2. 混淆检测
        obf = self.obfuscation_detector.detect(command, "zsh")
        if obf.detected:
            return ToolResult(
                success=False,
                error=f"禁止执行：检测到混淆模式 ({', '.join(obf.reasons[:2])})"
            )

        # 3. Preflight（若可解析脚本文件）
        try:
            wd = Path(workdir).resolve() if workdir else Path.cwd()
            validate_script_for_shell_bleed(command, wd)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))

        # 4. 代码助手场景：始终需用户确认（与 Cursor IDE 一致）
        if kwargs.get("_require_approval_always"):
            pending = self.approval_manager.create_pending(
                command=command,
                workdir=workdir,
                language="zsh",
                risk_level="safe",
                reason="代码助手执行前需用户确认",
                code=command,
                tool_name="exec"
            )
            return ToolResult(
                success=False,
                error="需要用户确认",
                data={
                    "requires_confirmation": True,
                    "approval_id": pending.id,
                    "command": command,
                    "reason": "代码助手执行前需用户确认",
                    "preview": {"command": command[:200], "risk_level": "safe"}
                }
            )

        # 5. Allowlist
        allow_result = self.allowlist_evaluator.evaluate(command, workdir, "zsh")
        if allow_result.satisfied:
            return await self._do_execute(command, workdir, timeout, background, use_pty)

        # 6. 风险检测
        risk_level, reason = self.risk_detector.detect_risk(command, "zsh")
        if not self.risk_detector.is_allowed(risk_level):
            return ToolResult(success=False, error=f"禁止执行：{reason}")
        if self.risk_detector.requires_confirmation(risk_level):
            pending = self.approval_manager.create_pending(
                command=command,
                workdir=workdir,
                language="zsh",
                risk_level=risk_level.value,
                reason=reason,
                code=command,
                tool_name="exec"
            )
            return ToolResult(
                success=False,
                error="需要用户确认",
                data={
                    "requires_confirmation": True,
                    "approval_id": pending.id,
                    "command": command,
                    "reason": reason,
                    "preview": {"command": command[:200], "risk_level": risk_level.value}
                }
            )

        return await self._do_execute(command, workdir, timeout, background, use_pty)

    async def _do_execute(
        self,
        command: str,
        workdir: str,
        timeout: int,
        background: bool,
        use_pty: bool = False
    ) -> ToolResult:
        def on_update(stdout: str, stderr: str):
            text = (stdout or "") + (stderr or "")
            if text:
                self.report_progress(text)

        result = await run_exec_process(
            command=command,
            workdir=workdir,
            timeout_sec=timeout,
            background=background,
            use_pty=use_pty,
            on_update=on_update
        )
        if result.backgrounded:
            return ToolResult(
                success=True,
                data={
                    "session_id": result.session_id,
                    "backgrounded": True,
                    "output": result.output,
                    "message": "已转为后台执行，使用 process 工具查看状态"
                }
            )
        return ToolResult(
            success=result.success,
            data={
                "output": result.output,
                "error": result.error,
                "exit_code": result.exit_code,
                "session_id": result.session_id
            },
            error=result.error if not result.success else None
        )
