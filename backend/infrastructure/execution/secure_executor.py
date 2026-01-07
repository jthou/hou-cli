"""安全执行包装器"""
import re
import logging
from typing import Optional
from pathlib import Path

from backend.infrastructure.execution.executor import SubprocessExecutor
from backend.infrastructure.execution.models import ExecutionRequest, ExecutionResult

logger = logging.getLogger(__name__)


class SecureExecutor:
    """安全执行包装器
    
    提供安全检查和命令过滤功能
    """
    
    # 允许的语言
    ALLOWED_LANGUAGES = ["python", "bash", "zsh", "powershell", "batch"]
    
    # 命令白名单
    COMMAND_WHITELIST = [
        "python", "python3", "py",
        "bash", "zsh", "sh",
        "pwsh", "powershell",
        "cmd", "cmd.exe"
    ]
    
    # 命令黑名单（危险命令）
    COMMAND_BLACKLIST = [
        "rm", "del", "format", "sudo", "su",
        "chmod", "chown", "chgrp",
        "mkfs", "fdisk", "dd",
        "killall", "pkill"
    ]
    
    # 禁止访问的路径
    RESTRICTED_PATHS = [
        "/etc", "/sys", "/proc", "/dev", "/root",
        "C:\\Windows\\System32", "C:\\Windows\\SysWOW64"
    ]
    
    # 代码长度限制（字节）
    MAX_CODE_LENGTH = 10 * 1024  # 10KB
    
    def __init__(self):
        """初始化安全执行器"""
        self.executor = SubprocessExecutor()
    
    def _validate_language(self, language: str) -> Optional[str]:
        """验证语言是否允许"""
        if language not in self.ALLOWED_LANGUAGES:
            return f"Language '{language}' is not allowed. Allowed languages: {', '.join(self.ALLOWED_LANGUAGES)}"
        return None
    
    def _check_command_blacklist(self, code: str) -> Optional[str]:
        """检查命令是否在黑名单中"""
        # 简单的关键词检查
        code_lower = code.lower()
        for dangerous_cmd in self.COMMAND_BLACKLIST:
            # 检查是否包含危险命令（作为独立命令，不是字符串的一部分）
            pattern = r'\b' + re.escape(dangerous_cmd) + r'\b'
            if re.search(pattern, code_lower):
                return f"Dangerous command '{dangerous_cmd}' is not allowed"
        return None
    
    def _check_restricted_paths(self, code: str) -> Optional[str]:
        """检查是否访问受限路径"""
        code_lower = code.lower()
        for restricted_path in self.RESTRICTED_PATHS:
            if restricted_path.lower() in code_lower:
                return f"Access to restricted path '{restricted_path}' is not allowed"
        return None
    
    def _validate_code_length(self, code: str) -> Optional[str]:
        """验证代码长度"""
        code_bytes = len(code.encode('utf-8'))
        if code_bytes > self.MAX_CODE_LENGTH:
            return f"Code is too long ({code_bytes} bytes). Maximum allowed: {self.MAX_CODE_LENGTH} bytes"
        return None
    
    def _validate_request(
        self, 
        request: ExecutionRequest,
        skip_blacklist_check: bool = False,
        skip_path_check: bool = False
    ) -> Optional[str]:
        """验证执行请求
        
        Args:
            request: 执行请求
            skip_blacklist_check: 是否跳过黑名单检查
            skip_path_check: 是否跳过路径检查
        """
        # 验证语言
        error = self._validate_language(request.language)
        if error:
            return error
        
        # 验证代码长度
        error = self._validate_code_length(request.code)
        if error:
            return error
        
        # 检查危险命令（如果未跳过）
        if not skip_blacklist_check:
            error = self._check_command_blacklist(request.code)
            if error:
                return error
        
        # 检查受限路径（如果未跳过）
        if not skip_path_check:
            error = self._check_restricted_paths(request.code)
            if error:
                return error
        
        return None
    
    async def execute_code_safely(
        self, 
        request: ExecutionRequest,
        skip_blacklist_check: bool = False,
        skip_path_check: bool = False
    ) -> ExecutionResult:
        """安全执行代码
        
        Args:
            request: 执行请求
            skip_blacklist_check: 是否跳过黑名单检查（用户确认后）
            skip_path_check: 是否跳过路径检查（用户确认后）
        """
        # 记录审计日志
        logger.info(f"Execution request: language={request.language}, code_length={len(request.code)}")
        
        # 验证请求（根据参数决定是否跳过某些检查）
        validation_error = self._validate_request(
            request, 
            skip_blacklist_check=skip_blacklist_check,
            skip_path_check=skip_path_check
        )
        if validation_error:
            logger.warning(f"Security validation failed: {validation_error}")
            return ExecutionResult(
                success=False,
                error=validation_error,
                language=request.language,
                code=request.code
            )
        
        # 执行代码
        try:
            result = await self.executor.execute(request)
            
            # 记录执行结果
            if result.success:
                logger.info(f"Execution succeeded: language={request.language}, exit_code={result.exit_code}")
            else:
                logger.warning(f"Execution failed: language={request.language}, error={result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Execution error: {str(e)}", exc_info=True)
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                language=request.language,
                code=request.code
            )
