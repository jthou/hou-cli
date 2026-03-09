"""代码执行引擎"""
import os
import sys
import asyncio
import tempfile
import shutil
import time
import platform
from pathlib import Path
from typing import Callable, Optional
import resource
import psutil

from backend.infrastructure.execution.models import (
    ExecutionRequest,
    ExecutionResult,
    ResourceUsage
)

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class SubprocessExecutor:
    """Subprocess 执行器（使用 subprocess + resource 限制）"""
    
    # 语言映射表（暂时仅支持 python、zsh）
    LANGUAGE_MAPPING = {
        "python": {
            "executors": {
                "linux": ["python3", "python"],
                "darwin": ["python3", "python"],
                "windows": ["python", "py"]
            },
            "execute_method": "code"
        },
        "zsh": {
            "executors": {
                "linux": ["zsh"],
                "darwin": ["zsh"],
                "windows": None  # Windows 不支持 zsh
            },
            "execute_method": "code"
        },
    }
    
    def __init__(self):
        """初始化执行器"""
        # 创建临时工作目录
        self.temp_base = Path(tempfile.gettempdir()) / "hou-cli-sandbox"
        self.temp_base.mkdir(parents=True, exist_ok=True)
    
    def _detect_platform(self) -> str:
        """检测当前平台"""
        system = platform.system().lower()
        if system == "darwin":
            return "darwin"
        elif system == "windows":
            return "windows"
        else:
            return "linux"
    
    def _get_executor_command(self, language: str, code: str) -> Optional[list]:
        """获取执行命令"""
        if language not in self.LANGUAGE_MAPPING:
            return None
        
        lang_config = self.LANGUAGE_MAPPING[language]
        platform_name = self._detect_platform()
        executors = lang_config["executors"].get(platform_name)
        
        if not executors:
            return None
        
        # 查找可用的执行器
        for executor in executors:
            if self._is_executor_available(executor):
                execute_method = lang_config["execute_method"]
                
                if execute_method == "code":
                    # Python, bash, zsh: 使用 -c 参数
                    return [executor, "-c", code]
                elif execute_method == "command":
                    # PowerShell: 使用 -Command 参数
                    return [executor, "-Command", code]
                elif execute_method == "file":
                    # Batch: 需要写入文件
                    # 这里暂时返回 None，需要先写入文件
                    return None
        
        return None
    
    def _is_executor_available(self, executor: str) -> bool:
        """检查执行器是否可用"""
        import shutil
        return shutil.which(executor) is not None
    
    def _create_work_dir(self) -> Path:
        """创建临时工作目录"""
        work_dir = self.temp_base / f"work_{os.getpid()}_{int(time.time())}"
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir
    
    def _cleanup_work_dir(self, work_dir: Path):
        """清理工作目录"""
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass  # 忽略清理错误
    
    def _set_resource_limits(self, memory_mb: Optional[int], cpu_seconds: Optional[int]):
        """设置资源限制（Linux/macOS）"""
        if platform.system() == "Windows":
            # Windows 不支持 resource 模块，主要依赖超时机制
            return
        
        try:
            if memory_mb:
                memory_bytes = memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            
            if cpu_seconds:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            
            # 文件描述符限制
            resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
        except Exception:
            # 如果设置失败，继续执行（某些系统可能不支持）
            pass

    def _safe_decode(self, data: bytes) -> str:
        """安全解码字节数据"""
        if not data:
            return ""
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            for enc in ["latin-1", "cp1252", "gbk", "gb2312"]:
                try:
                    return data.decode(enc, errors="replace")
                except Exception:
                    continue
            return data.decode("utf-8", errors="replace")

    async def _run_communicate(
        self,
        process: asyncio.subprocess.Process,
        timeout: int
    ) -> tuple:
        """使用 communicate 等待完成，返回 (output, error, exit_code)"""
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        output = self._safe_decode(stdout) if stdout else ""
        error = self._safe_decode(stderr) if stderr else ""
        return output, error, process.returncode or 0

    async def _run_streaming(
        self,
        process: asyncio.subprocess.Process,
        timeout: int,
        on_stdout: Optional[Callable[[str], None]],
        on_stderr: Optional[Callable[[str], None]],
    ) -> tuple:
        """逐块读取并回调，返回 (output, error, exit_code)"""
        out_buf: list = []
        err_buf: list = []

        async def read_stream(stream, is_stderr: bool):
            buf = out_buf if not is_stderr else err_buf
            cb = on_stderr if is_stderr else on_stdout
            while True:
                try:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    buf.append(text)
                    if cb:
                        cb(text)
                except Exception:
                    break

        await asyncio.wait_for(
            asyncio.gather(
                read_stream(process.stdout, False),
                read_stream(process.stderr, True),
                process.wait()
            ),
            timeout=timeout
        )
        output = "".join(out_buf)
        error = "".join(err_buf)
        return output, error, process.returncode or 0
    
    async def execute(
        self,
        request: ExecutionRequest,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> ExecutionResult:
        """
        执行代码。
        若 on_stdout/on_stderr 非空，则逐块读取并回调；否则使用 communicate()。
        """
        start_time = time.time()
        work_dir = None

        try:
            # 检查语言支持
            if request.language not in self.LANGUAGE_MAPPING:
                return ExecutionResult(
                    success=False,
                    error=f"Unsupported language: {request.language}",
                    language=request.language,
                    code=request.code
                )
            
            # 检查平台兼容性
            platform_name = self._detect_platform()
            lang_config = self.LANGUAGE_MAPPING[request.language]
            executors = lang_config["executors"].get(platform_name)
            
            if not executors:
                return ExecutionResult(
                    success=False,
                    error=f"Language {request.language} not supported on {platform_name}",
                    language=request.language,
                    code=request.code
                )
            
            # 获取执行命令
            command = self._get_executor_command(request.language, request.code)
            if not command:
                return ExecutionResult(
                    success=False,
                    error=f"No executor available for {request.language} on {platform_name}",
                    language=request.language,
                    code=request.code
                )
            
            # 创建临时工作目录
            work_dir = self._create_work_dir()
            
            # 创建进程
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=lambda: self._set_resource_limits(
                    request.memory_limit_mb,
                    request.timeout
                ) if platform.system() != "Windows" else None
            )

            use_streaming = on_stdout is not None or on_stderr is not None

            try:
                if use_streaming:
                    output, error, exit_code = await self._run_streaming(
                        process, request.timeout, on_stdout, on_stderr
                    )
                else:
                    output, error, exit_code = await self._run_communicate(
                        process, request.timeout
                    )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResult(
                    success=False,
                    error=f"Execution timeout after {request.timeout} seconds",
                    exit_code=-1,
                    language=request.language,
                    code=request.code
                )
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 获取资源使用情况（如果进程还在）
            resource_usage = ResourceUsage(
                execution_time_seconds=execution_time
            )
            
            try:
                if process.returncode is not None:
                    proc = psutil.Process(process.pid)
                    resource_usage.memory_used_mb = proc.memory_info().rss / 1024 / 1024
                    resource_usage.cpu_used_percent = proc.cpu_percent()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # 返回结果
            return ExecutionResult(
                success=exit_code == 0,
                output=output,
                error=error,
                exit_code=exit_code,
                resource_usage=resource_usage,
                language=request.language,
                code=request.code
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                exit_code=-1,
                language=request.language,
                code=request.code
            )
        finally:
            # 清理临时目录
            if work_dir:
                self._cleanup_work_dir(work_dir)
