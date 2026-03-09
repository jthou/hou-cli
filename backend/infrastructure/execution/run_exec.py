"""exec 进程执行

封装「启动进程 + 输出聚合 + 超时 + 后台」逻辑，供 exec 工具调用。
"""
import asyncio
import os
import platform
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from backend.infrastructure.execution.process_registry import (
    ProcessRegistry,
    ProcessSession,
    get_process_registry,
)


@dataclass
class RunExecResult:
    """执行结果"""
    session_id: str
    success: bool
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None
    backgrounded: bool = False


async def run_exec_process(
    command: str,
    workdir: str = "",
    env: Optional[dict] = None,
    timeout_sec: Optional[int] = None,
    use_pty: bool = False,
    background: bool = False,
    yield_ms: Optional[int] = None,
    on_update: Optional[Callable[[str, str], None]] = None,
) -> RunExecResult:
    """
    执行 shell 命令。

    Args:
        command: shell 命令（通过 zsh -c 执行）
        workdir: 工作目录
        env: 环境变量
        timeout_sec: 超时秒数
        use_pty: 是否使用 PTY（暂未实现）
        background: 是否立即后台
        yield_ms: 运行 N 毫秒后转为后台
        on_update: 输出回调 (stdout, stderr)

    Returns:
        RunExecResult
    """
    registry = get_process_registry()
    session_id = ProcessRegistry.create_session_id()

    # 构建执行命令：zsh -c 'command'
    shell_cmd = "zsh"
    if platform.system() == "Windows":
        return RunExecResult(
            session_id=session_id,
            success=False,
            error="exec 暂不支持 Windows"
        )
    if not shutil.which(shell_cmd):
        return RunExecResult(
            session_id=session_id,
            success=False,
            error=f"{shell_cmd} 未安装"
        )

    cwd = Path(workdir).resolve() if workdir else Path.cwd()
    if not cwd.exists():
        cwd = Path.cwd()

    session = ProcessSession(
        id=session_id,
        command=command,
        pid=None,
        cwd=str(cwd),
        started_at=time.time(),
        backgrounded=background
    )
    registry.add(session)

    proc_env = dict(os.environ) if env is None else {**os.environ, **env}

    use_pty_unix = use_pty and platform.system() != "Windows"
    master_fd = None
    slave_fd = None

    if use_pty_unix:
        try:
            import pty
            master_fd, slave_fd = pty.openpty()
        except ImportError:
            use_pty_unix = False

    try:
        if use_pty_unix and slave_fd is not None:
            proc = await asyncio.create_subprocess_exec(
                shell_cmd, "-c", command,
                cwd=str(cwd),
                env=proc_env,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd
            )
            os.close(slave_fd)
            slave_fd = None
        else:
            proc = await asyncio.create_subprocess_exec(
                shell_cmd, "-c", command,
                cwd=str(cwd),
                env=proc_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        session.pid = proc.pid

        async def read_stream(stream, is_stderr: bool):
            buf = []
            while True:
                try:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    buf.append(text)
                    registry.append_output(
                        session_id,
                        text if not is_stderr else "",
                        text if is_stderr else ""
                    )
                    if on_update:
                        on_update(text if not is_stderr else "", text if is_stderr else "")
                except Exception:
                    break
            return "".join(buf)

        async def read_pty_master():
            """从 PTY master 读取"""
            loop = asyncio.get_event_loop()
            buf = []
            while True:
                try:
                    data = await loop.run_in_executor(
                        None, lambda: os.read(master_fd, 4096)
                    )
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace")
                    buf.append(text)
                    registry.append_output(session_id, text, "")
                    if on_update:
                        on_update(text, "")
                except (OSError, ValueError):
                    break
            return "".join(buf)

        if use_pty_unix and master_fd is not None:
            try:
                if background or yield_ms:
                    async def bg_pty():
                        await read_pty_master()
                        await proc.wait()
                        registry.mark_exited(session_id, proc.returncode or 0)
                    asyncio.create_task(bg_pty())
                    if yield_ms:
                        await asyncio.sleep(min(yield_ms / 1000.0, 30))
                    registry.mark_backgrounded(session_id)
                    return RunExecResult(
                        session_id=session_id,
                        success=True,
                        output=registry.tail_output(session_id),
                        backgrounded=True
                    )
                try:
                    _, exit_code_raw = await asyncio.wait_for(
                        asyncio.gather(read_pty_master(), proc.wait()),
                        timeout=timeout_sec or 3600
                    )
                    exit_code = exit_code_raw or 0
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    registry.mark_exited(session_id, -9)
                    s = registry.get(session_id)
                    return RunExecResult(
                        session_id=session_id,
                        success=False,
                        output=s.aggregated if s else "",
                        error="执行超时",
                        exit_code=-9
                    )
                registry.mark_exited(session_id, exit_code)
                s = registry.get(session_id)
                return RunExecResult(
                    session_id=session_id,
                    success=exit_code == 0,
                    output=s.aggregated if s else "",
                    error="",
                    exit_code=exit_code
                )
            finally:
                try:
                    if master_fd is not None:
                        os.close(master_fd)
                except OSError:
                    pass

        if background or yield_ms:
            # 后台模式：启动读取任务，不等待完成
            async def bg_task():
                await read_stream(proc.stdout, False)
                await read_stream(proc.stderr, True)
                await proc.wait()
                registry.mark_exited(session_id, proc.returncode or 0)

            asyncio.create_task(bg_task())
            if yield_ms:
                await asyncio.sleep(min(yield_ms / 1000.0, 30))  # 最多等 30 秒
            registry.mark_backgrounded(session_id)
            return RunExecResult(
                session_id=session_id,
                success=True,
                output=registry.tail_output(session_id),
                backgrounded=True
            )

        # 同步模式：等待完成
        try:
            _, _, exit_code_raw = await asyncio.wait_for(
                asyncio.gather(
                    read_stream(proc.stdout, False),
                    read_stream(proc.stderr, True),
                    proc.wait()
                ),
                timeout=timeout_sec or 3600
            )
            exit_code = exit_code_raw or 0
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            registry.mark_exited(session_id, -9)
            s = registry.get(session_id)
            return RunExecResult(
                session_id=session_id,
                success=False,
                output=s.aggregated if s else "",
                error="执行超时",
                exit_code=-9
            )

        registry.mark_exited(session_id, exit_code)

        s = registry.get(session_id)
        aggregated = s.aggregated if s else ""

        return RunExecResult(
            session_id=session_id,
            success=exit_code == 0,
            output=aggregated,
            error="",
            exit_code=exit_code
        )

    except Exception as e:
        registry.mark_exited(session_id, -1)
        return RunExecResult(
            session_id=session_id,
            success=False,
            error=str(e),
            exit_code=-1
        )
