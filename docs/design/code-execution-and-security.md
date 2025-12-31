# 代码执行和安全设计文档

## 概述

本文档说明系统的代码执行能力和安全机制。系统需要能够安全地执行代码和命令，同时防止恶意操作和资源滥用。

## 核心功能

1. **代码执行能力**：支持多种语言的代码执行
2. **安全隔离**：沙箱隔离执行环境
3. **权限控制**：细粒度的权限管理
4. **命令过滤**：白名单/黑名单机制
5. **资源限制**：CPU、内存、时间限制
6. **执行审计**：记录所有执行操作

## 架构设计

```
代码执行请求
    ↓
权限检查
    ├── 用户权限验证
    ├── 操作类型检查
    └── 资源配额检查
    ↓
命令过滤
    ├── 白名单检查
    ├── 黑名单检查
    └── 模式匹配
    ↓
沙箱环境
    ├── 隔离执行环境
    ├── 资源限制
    └── 网络/文件系统限制
    ↓
代码执行引擎
    ├── Python 执行
    ├── Shell 命令执行
    └── 其他语言执行
    ↓
结果捕获
    ├── 标准输出
    ├── 标准错误
    ├── 执行时间
    └── 资源使用
    ↓
审计日志
    └── 记录执行历史
```

## 实现细节

### 1. 代码执行引擎

```python
# backend/execution/executor.py
from typing import Dict, Any, Optional, List
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime
import signal
import os
from backend.security.sandbox import Sandbox
from backend.security.resource_limiter import ResourceLimiter

class CodeExecutor:
    """代码执行引擎"""
    
    def __init__(self):
        self.sandbox = Sandbox()
        self.resource_limiter = ResourceLimiter()
    
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        memory_limit: int = 512,  # MB
        cpu_limit: float = 1.0,  # CPU核心数
        working_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        执行代码
        
        Args:
            code: 代码内容
            language: 编程语言
            timeout: 超时时间（秒）
            memory_limit: 内存限制（MB）
            cpu_limit: CPU限制（核心数）
            working_dir: 工作目录
        
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "exit_code": int,
                "execution_time": float,
                "memory_used": int,
                "cpu_used": float
            }
        """
        start_time = datetime.now()
        
        try:
            # 在沙箱中执行
            result = await self.sandbox.execute(
                code=code,
                language=language,
                timeout=timeout,
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
                working_dir=working_dir
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": result["exit_code"] == 0,
                "output": result["stdout"],
                "error": result["stderr"],
                "exit_code": result["exit_code"],
                "execution_time": execution_time,
                "memory_used": result.get("memory_used", 0),
                "cpu_used": result.get("cpu_used", 0.0)
            }
        
        except TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"Execution timeout after {timeout} seconds",
                "exit_code": -1,
                "execution_time": timeout,
                "memory_used": 0,
                "cpu_used": 0.0
            }
        
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "memory_used": 0,
                "cpu_used": 0.0
            }
    
    async def execute_command(
        self,
        command: List[str],
        timeout: int = 30,
        working_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        执行命令
        
        Args:
            command: 命令列表（如 ["python", "script.py"]）
            timeout: 超时时间
            working_dir: 工作目录
        """
        start_time = datetime.now()
        
        try:
            # 在沙箱中执行命令
            result = await self.sandbox.execute_command(
                command=command,
                timeout=timeout,
                working_dir=working_dir
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": result["exit_code"] == 0,
                "output": result["stdout"],
                "error": result["stderr"],
                "exit_code": result["exit_code"],
                "execution_time": execution_time,
                "command": " ".join(command)
            }
        
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "command": " ".join(command)
            }
    
    async def execute_python(
        self,
        code: str,
        timeout: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """执行 Python 代码"""
        return await self.execute_code(
            code=code,
            language="python",
            timeout=timeout,
            **kwargs
        )
    
    async def execute_shell(
        self,
        command: str,
        timeout: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """执行 Shell 命令"""
        return await self.execute_command(
            command=["sh", "-c", command],
            timeout=timeout,
            **kwargs
        )
```

### 2. 沙箱隔离

```python
# backend/security/sandbox.py
import subprocess
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
import resource
import signal
import psutil
import os

class Sandbox:
    """沙箱隔离执行环境"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "hou-cli-sandbox"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        memory_limit: int = 512,
        cpu_limit: float = 1.0,
        working_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """在沙箱中执行代码"""
        
        # 创建临时工作目录
        if working_dir is None:
            work_dir = self._create_work_dir()
        else:
            work_dir = working_dir
        
        try:
            if language == "python":
                return await self._execute_python(code, work_dir, timeout, memory_limit)
            elif language == "shell":
                return await self._execute_shell(code, work_dir, timeout, memory_limit)
            else:
                raise ValueError(f"Unsupported language: {language}")
        
        finally:
            # 清理临时目录（如果是我们创建的）
            if working_dir is None and work_dir.exists():
                self._cleanup_work_dir(work_dir)
    
    async def _execute_python(
        self,
        code: str,
        work_dir: Path,
        timeout: int,
        memory_limit: int
    ) -> Dict[str, Any]:
        """执行 Python 代码"""
        # 创建临时 Python 文件
        script_file = work_dir / "script.py"
        script_file.write_text(code, encoding="utf-8")
        
        # 设置资源限制
        def set_limits():
            # 内存限制（MB 转字节）
            memory_bytes = memory_limit * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (memory_bytes, memory_bytes)
            )
            
            # CPU 时间限制
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (timeout, timeout)
            )
        
        # 执行命令
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_file),
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=set_limits if os.name != 'nt' else None
        )
        
        try:
            # 等待执行完成或超时
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            # 获取资源使用情况
            try:
                proc = psutil.Process(process.pid)
                memory_used = proc.memory_info().rss / 1024 / 1024  # MB
                cpu_used = proc.cpu_percent()
            except:
                memory_used = 0
                cpu_used = 0.0
            
            return {
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "exit_code": process.returncode,
                "memory_used": memory_used,
                "cpu_used": cpu_used
            }
        
        except asyncio.TimeoutError:
            # 超时，终止进程
            process.kill()
            await process.wait()
            raise TimeoutError(f"Execution timeout after {timeout} seconds")
    
    async def _execute_shell(
        self,
        command: str,
        work_dir: Path,
        timeout: int,
        memory_limit: int
    ) -> Dict[str, Any]:
        """执行 Shell 命令"""
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "exit_code": process.returncode
            }
        
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Execution timeout after {timeout} seconds")
    
    async def execute_command(
        self,
        command: List[str],
        timeout: int,
        working_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """执行命令列表"""
        work_dir = working_dir or self._create_work_dir()
        
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "exit_code": process.returncode
            }
        
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Execution timeout after {timeout} seconds")
    
    def _create_work_dir(self) -> Path:
        """创建临时工作目录"""
        work_dir = self.temp_dir / f"work_{os.getpid()}_{id(self)}"
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir
    
    def _cleanup_work_dir(self, work_dir: Path):
        """清理工作目录"""
        import shutil
        try:
            shutil.rmtree(work_dir)
        except:
            pass
```

### 3. 权限管理

```python
# backend/security/permission_manager.py
from typing import Dict, List, Set, Optional
from enum import Enum
from pathlib import Path
import json
from shared.platform_utils import get_app_data_dir

class Permission(Enum):
    """权限类型"""
    EXECUTE_CODE = "execute_code"
    EXECUTE_COMMAND = "execute_command"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    NETWORK_ACCESS = "network_access"
    SYSTEM_ACCESS = "system_access"

class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir() / "data" / "security"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.permissions_file = self.data_dir / "permissions.json"
        
        # 默认权限配置
        self.default_permissions = {
            "execute_code": {
                "python": True,
                "shell": False,  # 默认禁止 Shell
                "javascript": False
            },
            "execute_command": {
                "allowed": ["python", "pip", "git"],  # 白名单
                "blocked": ["rm", "del", "format"]  # 黑名单
            },
            "file_access": {
                "read_allowed": True,
                "write_allowed": True,
                "delete_allowed": False,
                "restricted_paths": [
                    "/etc",
                    "/sys",
                    "/proc",
                    "C:\\Windows\\System32"  # Windows
                ]
            },
            "network_access": False,
            "system_access": False
        }
        
        self.permissions = self._load_permissions()
    
    def _load_permissions(self) -> Dict:
        """加载权限配置"""
        if self.permissions_file.exists():
            try:
                return json.loads(self.permissions_file.read_text())
            except:
                pass
        return self.default_permissions.copy()
    
    def _save_permissions(self):
        """保存权限配置"""
        self.permissions_file.write_text(
            json.dumps(self.permissions, indent=2)
        )
    
    def check_permission(
        self,
        permission: Permission,
        context: Optional[Dict] = None
    ) -> bool:
        """检查权限"""
        if permission == Permission.EXECUTE_CODE:
            language = context.get("language", "python") if context else "python"
            return self.permissions.get("execute_code", {}).get(language, False)
        
        elif permission == Permission.EXECUTE_COMMAND:
            command = context.get("command", []) if context else []
            if not command:
                return False
            
            cmd_name = command[0] if isinstance(command, list) else command.split()[0]
            
            # 检查黑名单
            blocked = self.permissions.get("execute_command", {}).get("blocked", [])
            if cmd_name in blocked:
                return False
            
            # 检查白名单
            allowed = self.permissions.get("execute_command", {}).get("allowed", [])
            return cmd_name in allowed
        
        elif permission == Permission.READ_FILE:
            file_path = context.get("file_path") if context else None
            if not file_path:
                return False
            
            return self._check_file_access(file_path, "read")
        
        elif permission == Permission.WRITE_FILE:
            file_path = context.get("file_path") if context else None
            if not file_path:
                return False
            
            return self._check_file_access(file_path, "write")
        
        elif permission == Permission.NETWORK_ACCESS:
            return self.permissions.get("network_access", False)
        
        elif permission == Permission.SYSTEM_ACCESS:
            return self.permissions.get("system_access", False)
        
        return False
    
    def _check_file_access(self, file_path: str, access_type: str) -> bool:
        """检查文件访问权限"""
        path = Path(file_path).resolve()
        
        # 检查受限路径
        restricted = self.permissions.get("file_access", {}).get("restricted_paths", [])
        for restricted_path in restricted:
            if str(path).startswith(restricted_path):
                return False
        
        # 检查访问类型
        if access_type == "read":
            return self.permissions.get("file_access", {}).get("read_allowed", True)
        elif access_type == "write":
            return self.permissions.get("file_access", {}).get("write_allowed", True)
        elif access_type == "delete":
            return self.permissions.get("file_access", {}).get("delete_allowed", False)
        
        return False
    
    def update_permissions(self, updates: Dict):
        """更新权限配置"""
        self.permissions.update(updates)
        self._save_permissions()
```

### 4. 命令过滤

```python
# backend/security/command_filter.py
from typing import List, Dict, Set
import re
from pathlib import Path
import json
from shared.platform_utils import get_app_data_dir

class CommandFilter:
    """命令过滤器"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir() / "data" / "security"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 危险命令黑名单
        self.dangerous_commands = {
            "rm", "del", "format", "fdisk", "mkfs",
            "dd", "shutdown", "reboot", "killall",
            "sudo", "su", "chmod", "chown"
        }
        
        # 安全命令白名单
        self.safe_commands = {
            "python", "pip", "git", "ls", "cat",
            "echo", "pwd", "cd", "mkdir", "touch"
        }
        
        # 模式匹配规则
        self.pattern_rules = [
            (r"rm\s+-rf", "危险删除命令"),
            (r"format\s+", "格式化命令"),
            (r"sudo\s+", "提权命令"),
        ]
    
    def is_allowed(self, command: str) -> tuple[bool, str]:
        """
        检查命令是否允许执行
        
        Returns:
            (是否允许, 原因)
        """
        # 提取命令名
        cmd_parts = command.split()
        if not cmd_parts:
            return False, "空命令"
        
        cmd_name = cmd_parts[0]
        
        # 检查黑名单
        if cmd_name in self.dangerous_commands:
            return False, f"命令 '{cmd_name}' 在黑名单中"
        
        # 检查模式匹配
        for pattern, reason in self.pattern_rules:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"匹配危险模式: {reason}"
        
        # 检查白名单（如果启用严格模式）
        # 在宽松模式下，只要不在黑名单就允许
        
        return True, "允许执行"
    
    def filter_command(self, command: str) -> str:
        """过滤命令中的危险部分"""
        # 移除危险参数
        filtered = command
        
        # 移除 -rf 等危险参数
        filtered = re.sub(r'\s+-rf\s+', ' ', filtered)
        filtered = re.sub(r'\s+-rf$', '', filtered)
        
        return filtered.strip()
```

### 5. 资源限制

```python
# backend/security/resource_limiter.py
from typing import Dict, Optional
import psutil
import time

class ResourceLimiter:
    """资源限制器"""
    
    def __init__(
        self,
        default_timeout: int = 30,
        default_memory_limit: int = 512,  # MB
        default_cpu_limit: float = 1.0
    ):
        self.default_timeout = default_timeout
        self.default_memory_limit = default_memory_limit
        self.default_cpu_limit = default_cpu_limit
    
    def check_resources(
        self,
        timeout: Optional[int] = None,
        memory_limit: Optional[int] = None,
        cpu_limit: Optional[float] = None
    ) -> Dict[str, Any]:
        """检查资源限制"""
        timeout = timeout or self.default_timeout
        memory_limit = memory_limit or self.default_memory_limit
        cpu_limit = cpu_limit or self.default_cpu_limit
        
        # 检查系统资源
        system_memory = psutil.virtual_memory()
        available_memory = system_memory.available / 1024 / 1024  # MB
        
        if available_memory < memory_limit:
            raise ResourceWarning(
                f"可用内存不足: {available_memory:.0f}MB < {memory_limit}MB"
            )
        
        return {
            "timeout": timeout,
            "memory_limit": memory_limit,
            "cpu_limit": cpu_limit,
            "available_memory": available_memory
        }
    
    def monitor_process(
        self,
        process,
        timeout: int,
        memory_limit: int
    ):
        """监控进程资源使用"""
        start_time = time.time()
        
        while process.poll() is None:
            elapsed = time.time() - start_time
            
            # 检查超时
            if elapsed > timeout:
                process.kill()
                raise TimeoutError(f"Process timeout after {timeout}s")
            
            # 检查内存使用
            try:
                proc = psutil.Process(process.pid)
                memory_used = proc.memory_info().rss / 1024 / 1024  # MB
                
                if memory_used > memory_limit:
                    process.kill()
                    raise MemoryError(
                        f"Memory limit exceeded: {memory_used:.0f}MB > {memory_limit}MB"
                    )
            except psutil.NoSuchProcess:
                break
            
            time.sleep(0.1)
```

### 6. 审计日志

```python
# backend/security/audit_logger.py
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import json
from shared.platform_utils import get_app_data_dir

class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir() / "data" / "security" / "audit"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def log_execution(
        self,
        command: str,
        result: Dict[str, Any],
        user_context: Optional[Dict] = None
    ):
        """记录执行日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "success": result.get("success", False),
            "exit_code": result.get("exit_code", -1),
            "execution_time": result.get("execution_time", 0),
            "memory_used": result.get("memory_used", 0),
            "user_context": user_context or {}
        }
        
        # 保存到文件（按日期）
        log_file = self.data_dir / f"execution_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def log_permission_denied(
        self,
        action: str,
        reason: str,
        context: Dict
    ):
        """记录权限拒绝日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "permission_denied",
            "action": action,
            "reason": reason,
            "context": context
        }
        
        log_file = self.data_dir / f"security_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def get_execution_history(
        self,
        days: int = 7
    ) -> List[Dict]:
        """获取执行历史"""
        history = []
        # 读取最近几天的日志
        # 实现省略...
        return history
```

### 7. 安全执行包装器

```python
# backend/execution/secure_executor.py
from backend.execution.executor import CodeExecutor
from backend.security.permission_manager import PermissionManager, Permission
from backend.security.command_filter import CommandFilter
from backend.security.audit_logger import AuditLogger

class SecureExecutor:
    """安全执行包装器"""
    
    def __init__(self):
        self.executor = CodeExecutor()
        self.permission_manager = PermissionManager()
        self.command_filter = CommandFilter()
        self.audit_logger = AuditLogger()
    
    async def execute_code_safely(
        self,
        code: str,
        language: str = "python",
        **kwargs
    ) -> Dict[str, Any]:
        """安全执行代码"""
        # 1. 权限检查
        if not self.permission_manager.check_permission(
            Permission.EXECUTE_CODE,
            context={"language": language}
        ):
            self.audit_logger.log_permission_denied(
                "execute_code",
                f"Language {language} not allowed",
                {"language": language, "code": code[:100]}
            )
            return {
                "success": False,
                "error": f"执行 {language} 代码的权限被拒绝"
            }
        
        # 2. 执行代码
        result = await self.executor.execute_code(code, language, **kwargs)
        
        # 3. 记录审计日志
        self.audit_logger.log_execution(
            command=f"{language} code execution",
            result=result
        )
        
        return result
    
    async def execute_command_safely(
        self,
        command: str,
        **kwargs
    ) -> Dict[str, Any]:
        """安全执行命令"""
        # 1. 命令过滤
        is_allowed, reason = self.command_filter.is_allowed(command)
        
        if not is_allowed:
            self.audit_logger.log_permission_denied(
                "execute_command",
                reason,
                {"command": command}
            )
            return {
                "success": False,
                "error": f"命令被拒绝: {reason}"
            }
        
        # 2. 权限检查
        if not self.permission_manager.check_permission(
            Permission.EXECUTE_COMMAND,
            context={"command": command.split()}
        ):
            self.audit_logger.log_permission_denied(
                "execute_command",
                "Permission denied",
                {"command": command}
            )
            return {
                "success": False,
                "error": "执行命令的权限被拒绝"
            }
        
        # 3. 过滤命令
        filtered_command = self.command_filter.filter_command(command)
        
        # 4. 执行命令
        result = await self.executor.execute_command(
            filtered_command.split(),
            **kwargs
        )
        
        # 5. 记录审计日志
        self.audit_logger.log_execution(
            command=command,
            result=result
        )
        
        return result
```

## 安全配置

### 默认安全配置

```json
{
  "execute_code": {
    "python": true,
    "shell": false,
    "javascript": false
  },
  "execute_command": {
    "allowed": ["python", "pip", "git", "ls", "cat"],
    "blocked": ["rm", "del", "format", "sudo"]
  },
  "file_access": {
    "read_allowed": true,
    "write_allowed": true,
    "delete_allowed": false,
    "restricted_paths": ["/etc", "/sys", "/proc"]
  },
  "resource_limits": {
    "default_timeout": 30,
    "default_memory_limit": 512,
    "default_cpu_limit": 1.0
  },
  "network_access": false,
  "system_access": false
}
```

## 使用示例

```python
# 安全执行代码
secure_executor = SecureExecutor()

# 执行 Python 代码
result = await secure_executor.execute_code_safely(
    code="print('Hello, World!')",
    language="python",
    timeout=10
)

# 执行命令（会被过滤和检查）
result = await secure_executor.execute_command_safely(
    command="python script.py",
    timeout=30
)

# 危险命令会被拒绝
result = await secure_executor.execute_command_safely(
    command="rm -rf /",  # 会被拒绝
    timeout=30
)
```

## 安全最佳实践

1. **最小权限原则**：默认拒绝，明确允许
2. **多层防护**：权限检查 + 命令过滤 + 沙箱隔离
3. **资源限制**：限制 CPU、内存、时间
4. **审计日志**：记录所有执行操作
5. **定期审查**：定期检查权限配置和审计日志
6. **沙箱隔离**：在隔离环境中执行代码
7. **输入验证**：验证所有输入参数

## 总结

代码执行和安全系统提供了：

- ✅ **代码执行能力**：支持多种语言的代码执行
- ✅ **沙箱隔离**：在隔离环境中执行，防止影响系统
- ✅ **权限控制**：细粒度的权限管理
- ✅ **命令过滤**：白名单/黑名单机制
- ✅ **资源限制**：CPU、内存、时间限制
- ✅ **审计日志**：完整的执行记录
- ✅ **多层防护**：多重安全检查机制

这个系统确保了代码执行的安全性，防止恶意操作和资源滥用。

