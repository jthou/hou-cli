"""代码执行工具实现"""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.infrastructure.execution import SecureExecutor, ExecutionRequest
from backend.infrastructure.execution.risk_detector import RiskDetector, RiskLevel

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


class CodeExecutorTool(Tool):
    """代码执行工具
    
    允许 AI 助手在安全的沙盒环境中执行脚本代码。
    支持 Python、bash、zsh、PowerShell、batch 等脚本语言。
    """
    
    def __init__(self):
        """初始化代码执行工具"""
        # 获取安全执行器的配置，用于生成工具描述
        executor = SecureExecutor()
        dangerous_commands = executor.COMMAND_BLACKLIST
        restricted_paths = executor.RESTRICTED_PATHS
        
        # 将危险命令分类展示
        file_delete_cmds = [cmd for cmd in dangerous_commands if cmd in ["rm", "del"]]
        permission_cmds = [cmd for cmd in dangerous_commands if cmd in ["sudo", "su", "chmod", "chown", "chgrp"]]
        disk_cmds = [cmd for cmd in dangerous_commands if cmd in ["format", "mkfs", "fdisk", "dd"]]
        process_cmds = [cmd for cmd in dangerous_commands if cmd in ["killall", "pkill"]]
        
        # 构建危险命令描述
        dangerous_cmds_desc = ""
        if file_delete_cmds:
            dangerous_cmds_desc += f"- 文件删除：{', '.join(file_delete_cmds)}\n"
        if permission_cmds:
            dangerous_cmds_desc += f"- 权限管理：{', '.join(permission_cmds)}\n"
        if disk_cmds:
            dangerous_cmds_desc += f"- 磁盘操作：{', '.join(disk_cmds)}\n"
        if process_cmds:
            dangerous_cmds_desc += f"- 进程管理：{', '.join(process_cmds)}\n"
        
        # 构建受限路径描述
        restricted_paths_desc = ""
        linux_paths = [p for p in restricted_paths if not p.startswith("C:")]
        windows_paths = [p for p in restricted_paths if p.startswith("C:")]
        if linux_paths:
            restricted_paths_desc += f"- Linux/macOS: {', '.join(linux_paths)}\n"
        if windows_paths:
            restricted_paths_desc += f"- Windows: {', '.join(windows_paths)}\n"
        
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
                "在安全的沙盒环境中执行脚本代码（每次独立执行，不保留状态）。"
                "\n【优先使用场景】当需要以下功能时，优先使用 execute_code 而非 jupyter："
                "\n1. 一次性脚本任务："
                "   - 执行独立的脚本，不需要保留变量或状态"
                "   - 例如：读取文件、处理数据、输出结果（一次性完成）"
                "\n2. 系统操作和文件管理："
                "   - 文件操作（创建、删除、移动、复制文件）"
                "   - 系统命令（bash、zsh、powershell、batch）"
                "   - 环境检查和配置"
                "\n3. 数据转换和验证："
                "   - 一次性数据转换任务"
                "   - 数据格式验证"
                "   - 简单的数据处理（不需要保留中间结果）"
                "\n4. 跨语言支持："
                "   - 需要执行非 Python 代码（bash、zsh、powershell、batch）"
                "\n支持的语言："
                "- python: Python 脚本（跨平台）"
                "- bash: Bash 脚本（Linux/macOS）"
                "- zsh: Zsh 脚本（macOS）"
                "- powershell: PowerShell 脚本（Windows/跨平台）"
                "- batch: Batch 脚本（Windows）"
                "\n核心特性："
                "- ✅ 独立执行：每次执行都是全新的环境，不保留之前的状态"
                "- ✅ 多语言支持：支持 Python、bash、zsh、powershell、batch"
                "- ✅ 系统操作：可以执行系统命令和文件操作"
                "- ✅ 安全隔离：代码在隔离环境中执行"
                "\n与 jupyter 的区别："
                "- execute_code: 每次独立执行，不保留状态，适合一次性任务和系统操作"
                "- jupyter: 保留状态，适合需要多次交互、逐步构建的复杂数据分析任务"
                "\n如何与 jupyter 结合使用："
                "- 先用 execute_code 准备环境：下载数据、创建目录、安装依赖、配置环境"
                "- 再用 jupyter 进行分析：在 jupyter 中加载数据、分析、可视化、训练模型"
                "- 先用 jupyter 开发和测试：在 jupyter 中编写代码、测试功能、调试"
                "- 再用 execute_code 部署和自动化：将 jupyter 中的代码整理成脚本，用 execute_code 执行"
                "- 先用 execute_code 执行系统操作：文件操作、环境检查、依赖安装"
                "- 再用 jupyter 进行交互式开发：数据分析、模型训练、结果探索"
                "\n协作示例："
                "- 场景1：'分析 CSV 文件并生成报告'"
                "  1. 使用 execute_code 下载/检查 CSV 文件（系统操作）"
                "  2. 使用 jupyter 加载数据、分析、可视化（数据分析）"
                "  3. 使用 execute_code 保存报告到文件（文件操作）"
                "- 场景2：'训练机器学习模型并部署'"
                "  1. 使用 execute_code 准备数据文件、安装依赖（环境准备）"
                "  2. 使用 jupyter 训练模型、评估、调优（模型开发）"
                "  3. 使用 execute_code 保存模型、创建部署脚本（部署）"
                "- 场景3：'数据处理流水线'"
                "  1. 使用 execute_code 下载原始数据、清理目录（数据准备）"
                "  2. 使用 jupyter 数据清洗、转换、分析（数据处理）"
                "  3. 使用 execute_code 保存处理后的数据、运行批处理（自动化）"
                "\n核心原则（非常重要）："
                "- 严格按照用户指令执行，不要添加额外的探索、检查或推理"
                "- 用户要求执行什么命令，就执行什么命令，不要自作主张添加其他操作"
                "- 例如：用户要求 '显示 /home 下的所有文件'，直接执行 'ls /home'，不要去找 /dev、/Users 等其他路径"
                "- 优先使用简单、直接的命令，避免不必要的复杂性"
                "- 能用单条命令解决的问题，不要写多行代码"
                "\n示例场景："
                "- '读取文件内容' → 使用 execute_code（一次性任务）"
                "- '列出目录文件' → 使用 execute_code（系统操作）"
                "- '执行 bash 脚本' → 使用 execute_code（多语言支持）"
                "- '分析数据并绘制图表' → 使用 jupyter（需要保留数据和可视化）"
                "\n安全限制："
                "- 代码在隔离环境中执行"
                "- 资源限制：CPU、内存、时间"
                "- 代码长度限制：10KB"
                "- 输出大小限制：10MB"
                "\n【重要】禁止使用的危险命令（会被拒绝执行）："
                f"{dangerous_cmds_desc}"
                "- 注意：这些命令即使作为字符串的一部分也会被检测到，请避免使用"
                "\n【重要】禁止访问的敏感目录（会被拒绝执行）："
                f"{restricted_paths_desc}"
                "- 注意：代码中包含这些路径会被拒绝执行"
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
            
            # 安全处理输出和错误（清理无效字符）
            def safe_clean_text(text: str) -> str:
                """安全清理文本，移除无效字符"""
                # #region agent log
                try:
                    import json
                    debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
                    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(debug_log_path, 'a', encoding='utf-8') as f:
                        json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"code_executor_tool.py:safe_clean_text","message":"开始清理文本","data":{"text_type":type(text).__name__,"text_len":len(str(text)) if text else 0},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                        f.write('\n')
                except: pass
                # #endregion
                if not text:
                    return ""
                try:
                    # 尝试编码和解码，清理无效字符
                    result = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                    # #region agent log
                    try:
                        debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
                        debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(debug_log_path, 'a', encoding='utf-8') as f:
                            json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"code_executor_tool.py:safe_clean_text","message":"文本清理成功","data":{"result_len":len(result)},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                            f.write('\n')
                    except: pass
                    # #endregion
                    return result
                except Exception as e:
                    # #region agent log
                    try:
                        debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
                        debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(debug_log_path, 'a', encoding='utf-8') as f:
                            json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"code_executor_tool.py:safe_clean_text","message":"文本清理失败","data":{"error":str(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                            f.write('\n')
                    except: pass
                    # #endregion
                    # 如果失败，返回清理后的版本
                    return str(text).encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            
            # #region agent log
            try:
                import json
                debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
                debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(debug_log_path, 'a', encoding='utf-8') as f:
                    json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"code_executor_tool.py:_execute_async","message":"构建工具结果","data":{"result_success":result.success,"output_len":len(result.output) if result.output else 0,"error_len":len(result.error) if result.error else 0},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                    f.write('\n')
            except: pass
            # #endregion
            # 构建返回结果
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

