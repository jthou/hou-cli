"""交互式执行器（后端）

使用 pexpect 处理需要交互式输入的代码执行
"""
import logging
import platform
from typing import Callable, Optional
from backend.infrastructure.execution.models import ExecutionRequest, ExecutionResult, ResourceUsage

logger = logging.getLogger(__name__)

try:
    import pexpect
    PEXPECT_AVAILABLE = True
except ImportError:
    PEXPECT_AVAILABLE = False
    logger.warning("pexpect 未安装，交互式执行功能不可用")


class InteractiveExecutor:
    """交互式执行器
    
    使用 pexpect 处理需要交互式输入的代码执行
    """
    
    def __init__(self):
        """初始化交互式执行器"""
        if not PEXPECT_AVAILABLE:
            raise ImportError("pexpect 未安装，无法使用交互式执行器")
    
    def detect_interactive_input(self, code: str, language: str) -> bool:
        """检测代码是否需要交互式输入
        
        Args:
            code: 代码内容
            language: 代码语言
            
        Returns:
            是否需要交互式输入
        """
        code_lower = code.lower()
        
        # Python
        if language == "python":
            if "input(" in code:
                return True
        
        # Shell (bash/zsh)
        if language in ["bash", "zsh"]:
            if "read " in code:
                return True
            # 交互式命令
            interactive_commands = ["sudo", "passwd", "ssh", "scp"]
            for cmd in interactive_commands:
                if cmd in code_lower:
                    return True
        
        # PowerShell
        if language == "powershell":
            if "Read-Host" in code or "$input" in code:
                return True
        
        return False
    
    async def execute_interactive(
        self,
        code: str,
        language: str,
        timeout: int,
        input_handler: Callable[[str, bool], str]
    ) -> ExecutionResult:
        """执行需要交互式输入的代码
        
        Args:
            code: 代码内容
            language: 代码语言
            timeout: 超时时间（秒）
            input_handler: 输入处理函数，参数为 (prompt, is_password)，返回用户输入
            
        Returns:
            执行结果
        """
        if not PEXPECT_AVAILABLE:
            return ExecutionResult(
                success=False,
                error="pexpect 未安装，无法执行交互式代码",
                language=language,
                code=code
            )
        
        # 构建执行命令
        command = self._build_command(code, language)
        if not command:
            return ExecutionResult(
                success=False,
                error=f"无法为语言 {language} 构建执行命令",
                language=language,
                code=code
            )
        
        try:
            # 创建进程
            child = pexpect.spawn(
                command,
                encoding='utf-8',
                timeout=timeout
            )
            
            output_lines = []
            error_lines = []
            
            # 监听输出，检测需要输入的地方
            while True:
                try:
                    # 等待输出或输入提示
                    index = child.expect([
                        pexpect.EOF,
                        pexpect.TIMEOUT,
                        r'password:',
                        r'Password:',
                        r'请输入.*[:：]',
                        r'>>>',
                        r'In \[.*\]:',
                        r'\$ ',  # Shell prompt
                        r'# ',   # Root prompt
                    ], timeout=1)
                    
                    # 收集输出
                    if child.before:
                        output_lines.append(child.before)
                    
                    if index == 0:  # EOF
                        break
                    elif index == 1:  # TIMEOUT
                        # 超时，继续等待
                        continue
                    elif index in [2, 3]:  # 密码输入
                        prompt = child.after.decode('utf-8', errors='ignore') if isinstance(child.after, bytes) else child.after
                        user_input = input_handler(prompt, is_password=True)
                        child.sendline(user_input)
                    elif index == 4:  # 中文输入提示
                        prompt = child.after.decode('utf-8', errors='ignore') if isinstance(child.after, bytes) else child.after
                        user_input = input_handler(prompt, is_password=False)
                        child.sendline(user_input)
                    elif index in [5, 6]:  # Python/IPython prompt
                        # 交互式 Python 会话，暂时跳过
                        # TODO: 支持交互式 Python 会话
                        break
                    elif index in [7, 8]:  # Shell prompt
                        # Shell 提示符，可能等待输入
                        # 检查是否有未完成的命令
                        if code.strip().endswith('\\'):
                            # 多行命令，继续
                            continue
                        else:
                            # 命令完成
                            break
                    else:
                        # 其他情况，继续
                        continue
                        
                except pexpect.EOF:
                    break
                except pexpect.TIMEOUT:
                    # 超时，检查是否还在运行
                    if not child.isalive():
                        break
                    continue
            
            # 获取最终输出
            if child.before:
                output_lines.append(child.before)
            
            # 等待进程结束
            child.close()
            exit_code = child.exitstatus if child.exitstatus is not None else -1
            
            # 合并输出
            output = ''.join(output_lines).strip()
            error = ''.join(error_lines).strip() if error_lines else ""
            
            return ExecutionResult(
                success=exit_code == 0,
                output=output,
                error=error if exit_code != 0 else "",
                exit_code=exit_code,
                resource_usage=ResourceUsage(execution_time_seconds=0),  # TODO: 计算实际执行时间
                language=language,
                code=code
            )
            
        except Exception as e:
            logger.error(f"交互式执行失败: {str(e)}", exc_info=True)
            return ExecutionResult(
                success=False,
                error=f"交互式执行失败: {str(e)}",
                language=language,
                code=code
            )
    
    def _build_command(self, code: str, language: str) -> Optional[str]:
        """构建执行命令
        
        Args:
            code: 代码内容
            language: 代码语言
            
        Returns:
            执行命令，如果无法构建则返回 None
        """
        system = platform.system().lower()
        
        if language == "python":
            if system == "windows":
                return f"python -c {code!r}"
            else:
                return f"python3 -c {code!r}"
        elif language == "bash":
            if system == "windows":
                return None  # Windows 不支持 bash
            return f"bash -c {code!r}"
        elif language == "zsh":
            if system == "windows":
                return None  # Windows 不支持 zsh
            return f"zsh -c {code!r}"
        elif language == "powershell":
            if system == "windows":
                return f"powershell -Command {code!r}"
            else:
                return f"pwsh -Command {code!r}"
        elif language == "batch":
            if system != "windows":
                return None  # 非 Windows 不支持 batch
            return f"cmd /c {code}"
        else:
            return None


