"""安全执行包装器"""
import re
import logging
import os
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
    
    def __init__(self):
        """初始化安全执行器"""
        self.executor = SubprocessExecutor()

        # 从环境变量读取代码长度限制（单位：KB，默认10KB）
        max_code_kb = int(os.getenv("MAX_CODE_LENGTH_KB", "10"))
        self.MAX_CODE_LENGTH = max_code_kb * 1024

        logger.info(f"代码长度限制设置为: {self.MAX_CODE_LENGTH} 字节 ({max_code_kb}KB)")
    
    def _validate_language(self, language: str) -> Optional[str]:
        """验证语言是否允许"""
        if language not in self.ALLOWED_LANGUAGES:
            return f"Language '{language}' is not allowed. Allowed languages: {', '.join(self.ALLOWED_LANGUAGES)}"
        return None
    
    def _check_command_blacklist(self, code: str) -> Optional[str]:
        """检查命令是否在黑名单中
        
        智能识别真正的命令调用，避免误判：
        - 排除字符串字面量中的匹配（单引号、双引号、三引号）
        - 排除字典键访问（如 ['format'], ["format"]）
        - 排除变量名中的匹配（如 format_info）
        - 只匹配真正的命令调用模式
        """
        code_lower = code.lower()
        
        # 检测是否是 Python 代码
        is_python_code = any(keyword in code_lower for keyword in ['import ', 'def ', 'class ', 'print(', 'if __name__'])
        
        for dangerous_cmd in self.COMMAND_BLACKLIST:
            if is_python_code:
                # Python 代码：需要更智能的检测
                
                # 1. 先检查是否是真正的命令调用模式（优先级最高）
                # 匹配模式：subprocess 调用、os.system 调用、os.popen 调用等
                # 注意：即使命令在字符串中，如果是命令调用，也应该阻止
                command_patterns = [
                    r'subprocess\.(call|run|Popen|check_call|check_output)\([^)]*["\']' + re.escape(dangerous_cmd),  # subprocess 调用
                    r'os\.system\([^)]*["\']' + re.escape(dangerous_cmd),  # os.system 调用
                    r'os\.popen\([^)]*["\']' + re.escape(dangerous_cmd),  # os.popen 调用
                    r'Popen\([^)]*["\']' + re.escape(dangerous_cmd),  # Popen 调用
                ]
                
                # 检查是否是真正的命令调用
                is_command_call = any(re.search(pattern, code_lower) for pattern in command_patterns)
                if is_command_call:
                    return f"Dangerous command '{dangerous_cmd}' is not allowed"
                
                # 2. 排除字典键访问模式（优先级次之）
                dict_key_patterns = [
                    r"\[['\"]" + re.escape(dangerous_cmd) + r"['\"]\]",  # ['format'], ["format"]
                    r"\.get\(['\"]" + re.escape(dangerous_cmd) + r"['\"]",  # .get('format')
                    r"\[['\"]" + re.escape(dangerous_cmd) + r"['\"]\s*:",  # {'format': ...}
                ]
                if any(re.search(pattern, code_lower) for pattern in dict_key_patterns):
                    # 是字典键访问，跳过
                    continue
                
                # 3. 排除普通字符串字面量中的匹配（优先级最低）
                # 匹配单引号、双引号、三引号字符串（包括多行字符串）
                # 但排除已经在命令调用中的情况（上面已处理）
                string_patterns = [
                    r"['\"][^'\"]*" + re.escape(dangerous_cmd) + r"[^'\"]*['\"]",  # 单行字符串
                    r'"""[\s\S]*?' + re.escape(dangerous_cmd) + r'[\s\S]*?"""',  # 三引号字符串
                    r"'''[\s\S]*?" + re.escape(dangerous_cmd) + r"[\s\S]*?'''",  # 三单引号字符串
                ]
                if any(re.search(pattern, code_lower) for pattern in string_patterns):
                    # 在字符串中，跳过
                    continue
            else:
                # 非 Python 代码（bash、zsh、powershell 等）
                # 排除引号字符串中的匹配
                string_pattern = r'["\'][^"\']*' + re.escape(dangerous_cmd) + r'[^"\']*["\']'
                if re.search(string_pattern, code_lower):
                    continue
                
                # 匹配独立的命令（单词边界，且不在字符串中）
                # 匹配行首、空格后、分号后、管道后的命令
                command_patterns = [
                    r'^\s*' + re.escape(dangerous_cmd) + r'\b',  # 行首
                    r'[;\n|&]\s*' + re.escape(dangerous_cmd) + r'\b',  # 分号、换行、管道、&& 后
                    r'\$\(' + re.escape(dangerous_cmd) + r'\b',  # $(format ...) 命令替换
                    r'`' + re.escape(dangerous_cmd) + r'\b',  # `format ...` 命令替换
                ]
                
                if any(re.search(pattern, code_lower) for pattern in command_patterns):
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
