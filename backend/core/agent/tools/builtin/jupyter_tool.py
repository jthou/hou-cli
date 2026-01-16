"""Jupyter Notebook 工具实现"""

import asyncio
import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)

# 尝试导入 jupyter_client
try:
    from jupyter_client import KernelManager
    from jupyter_client.blocking import BlockingKernelClient
    from jupyter_client.kernelspec import find_kernel_specs
    JUPYTER_AVAILABLE = True
except ImportError:
    JUPYTER_AVAILABLE = False
    KernelManager = None
    BlockingKernelClient = None
    find_kernel_specs = None


class JupyterTool(Tool):
    """Jupyter Notebook 工具
    
    允许 AI 助手在 Jupyter kernel 中执行代码，支持交互式编程、
    数据分析和可视化。代码执行结果会保留在 kernel 的内存中，
    支持跨代码块的变量共享。
    """
    
    def __init__(self):
        """初始化 Jupyter 工具"""
        parameters = [
            ToolParameter(
                name="code",
                type="string",
                description=(
                    "要在 Jupyter kernel 中执行的代码。"
                    "\n支持 Python 代码，可以包含："
                    "- 变量定义和计算"
                    "- 数据分析和处理（pandas, numpy 等）"
                    "- 数据可视化（matplotlib, plotly 等）"
                    "- 机器学习（sklearn, tensorflow 等）"
                    "\n注意："
                    "- 代码会在同一个 kernel 会话中执行，变量会保留"
                    "- 可以使用之前执行的代码中定义的变量"
                    "- 支持多行代码和复杂逻辑"
                ),
                required=True
            ),
            ToolParameter(
                name="kernel_name",
                type="string",
                description=(
                    "Jupyter kernel 名称（可选）。"
                    "\n默认使用 'python3' 或 'python'。"
                    "\n常见选项：'python3', 'python', 'ipython', 'julia', 'r' 等"
                ),
                required=False,
                default="python3"
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="执行超时时间（秒），默认 60，最大 300",
                required=False,
                default=60
            ),
            ToolParameter(
                name="clear_output",
                type="boolean",
                description="是否在执行前清除之前的输出（默认 False，保留历史）",
                required=False,
                default=False
            )
        ]
        
        # 根据依赖是否可用，调整工具描述
        if JUPYTER_AVAILABLE:
            description = (
                "Jupyter Notebook 工具，在 Jupyter kernel 中执行 Python 代码。"
                "\n【优先使用场景】当需要以下功能时，优先使用 jupyter 而非 execute_code："
                "\n1. 交互式数据分析："
                "   - 需要多次执行代码，且后续代码依赖前面代码的变量和结果"
                "   - 例如：先加载数据，再处理数据，最后可视化"
                "   - 例如：先定义函数，再调用函数，再分析结果"
                "\n2. 数据可视化："
                "   - 需要创建图表、绘制图形（matplotlib、plotly、seaborn 等）"
                "   - 需要显示图像、HTML 输出等富媒体内容"
                "\n3. 机器学习工作流："
                "   - 训练模型后需要评估、预测、可视化"
                "   - 需要保留模型对象、数据预处理结果等"
                "\n4. 科学计算和探索："
                "   - 需要逐步探索数据，尝试不同的分析方法"
                "   - 需要保留中间计算结果，避免重复计算"
                "\n核心特性："
                "- ✅ 状态保留：变量、函数、导入的模块在 kernel 中保留"
                "- ✅ 跨代码块：可以在多个代码块之间共享变量"
                "- ✅ 可视化支持：支持 matplotlib、plotly 等可视化库"
                "- ✅ 富媒体输出：支持图像、HTML、表格等输出格式"
                "\n与 execute_code 的区别："
                "- execute_code: 每次独立执行，不保留状态，适合一次性脚本任务"
                "- jupyter: 保留状态，适合需要多次交互、逐步构建的复杂任务"
                "\n如何与 execute_code 结合使用："
                "- 先用 execute_code 准备数据：下载文件、清理目录、准备输入数据"
                "- 再用 jupyter 分析数据：在 jupyter 中加载数据、分析、可视化"
                "- 先用 execute_code 执行系统操作：检查环境、安装依赖、配置环境"
                "- 再用 jupyter 进行开发：在 jupyter 中编写和测试代码"
                "- 先用 jupyter 探索和分析：数据分析、模型训练、结果可视化"
                "- 再用 execute_code 部署和自动化：将 jupyter 中的代码整理成脚本，用 execute_code 执行"
                "\n示例场景："
                "- '加载数据并分析' → 使用 jupyter（需要保留数据）"
                "- '绘制销售趋势图' → 使用 jupyter（可视化）"
                "- '训练模型并评估' → 使用 jupyter（需要保留模型）"
                "- '执行一个简单的 Python 脚本' → 使用 execute_code（一次性任务）"
                "\n协作示例："
                "- 场景1：'分析 CSV 文件并生成报告'"
                "  1. 使用 execute_code 下载/检查 CSV 文件（系统操作）"
                "  2. 使用 jupyter 加载数据、分析、可视化（数据分析）"
                "  3. 使用 execute_code 保存报告到文件（文件操作）"
                "- 场景2：'训练机器学习模型并部署'"
                "  1. 使用 execute_code 准备数据文件（数据准备）"
                "  2. 使用 jupyter 训练模型、评估、调优（模型开发）"
                "  3. 使用 execute_code 保存模型、部署脚本（部署）"
            )
        else:
            description = (
                "Jupyter Notebook 工具（需要安装依赖）。"
                "\n要使用此工具，请先安装："
                "pip install jupyter-client ipykernel"
            )
        
        super().__init__(
            name="jupyter",
            description=description,
            parameters=parameters
        )
        
        # Kernel 管理器（延迟初始化）
        self._kernel_manager: Optional[KernelManager] = None
        self._kernel_client: Optional[BlockingKernelClient] = None
        self._kernel_name = "python3"
    
    def _ensure_kernel(self, kernel_name: str = "python3"):
        """确保 kernel 已启动"""
        if not JUPYTER_AVAILABLE:
            raise ImportError(
                "jupyter-client is not installed. "
                "Please install it with: pip install jupyter-client ipykernel"
            )
        
        # 如果 kernel 已启动且名称相同，直接返回
        if self._kernel_client is not None and self._kernel_name == kernel_name:
            try:
                # 检查 kernel 是否还活着
                if self._kernel_client.is_alive():
                    return
            except Exception:
                # Kernel 已死，需要重启
                self._cleanup_kernel()
        
        # 启动新的 kernel
        try:
            # 查找可用的 kernel
            kernels = find_kernel_specs()
            if kernel_name not in kernels:
                # 尝试使用 python3 或 python
                if "python3" in kernels:
                    kernel_name = "python3"
                elif "python" in kernels:
                    kernel_name = "python"
                else:
                    # 使用第一个可用的 kernel
                    kernel_name = list(kernels.keys())[0] if kernels else "python3"
                    logger.warning(f"指定的 kernel 不存在，使用 {kernel_name}")
            
            # 创建 kernel 管理器
            self._kernel_manager = KernelManager(kernel_name=kernel_name)
            self._kernel_manager.start_kernel()
            
            # 创建 kernel 客户端
            self._kernel_client = self._kernel_manager.blocking_client()
            self._kernel_client.start_channels()
            self._kernel_name = kernel_name
            
            logger.info(f"Jupyter kernel '{kernel_name}' 已启动")
            
        except Exception as e:
            logger.error(f"启动 Jupyter kernel 失败: {e}", exc_info=True)
            raise RuntimeError(f"无法启动 Jupyter kernel: {str(e)}")
    
    def _cleanup_kernel(self):
        """清理 kernel 资源"""
        try:
            if self._kernel_client is not None:
                self._kernel_client.stop_channels()
                self._kernel_client = None
            if self._kernel_manager is not None:
                self._kernel_manager.shutdown_kernel()
                self._kernel_manager = None
        except Exception as e:
            logger.warning(f"清理 kernel 资源时出错: {e}")
    
    def execute(self, **kwargs) -> ToolResult:
        """执行 Jupyter 代码（同步包装异步方法）"""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self._execute_async(**kwargs)
                )
                timeout = kwargs.get("timeout", 60) + 10
                return future.result(timeout=timeout)
        except RuntimeError:
            return asyncio.run(self._execute_async(**kwargs))
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行 Jupyter 代码"""
        if not JUPYTER_AVAILABLE:
            return ToolResult(
                success=False,
                error=(
                    "jupyter-client is not installed. "
                    "Please install it with: pip install jupyter-client ipykernel"
                )
            )
        
        code = kwargs.get("code")
        if not code:
            return ToolResult(
                success=False,
                error="code 参数是必需的"
            )
        
        kernel_name = kwargs.get("kernel_name", "python3")
        timeout = kwargs.get("timeout", 60)
        clear_output = kwargs.get("clear_output", False)
        
        # 验证超时时间
        if timeout < 1 or timeout > 300:
            timeout = 60
        
        try:
            # 确保 kernel 已启动
            self._ensure_kernel(kernel_name)
            
            # 如果需要清除输出
            if clear_output:
                try:
                    self._kernel_client.execute("", timeout=1.0)
                except Exception:
                    pass
            
            # 执行代码
            # 使用 execute 方法执行代码
            msg_id = self._kernel_client.execute(code)
            
            # 等待执行完成并获取结果
            output_parts = []
            error_parts = []
            
            # 获取执行结果
            while True:
                try:
                    msg = self._kernel_client.get_iopub_msg(timeout=timeout)
                    msg_type = msg['msg_type']
                    content = msg.get('content', {})
                    
                    if msg_type == 'stream':
                        # 标准输出或标准错误
                        stream_name = content.get('name', 'stdout')
                        text = content.get('text', '')
                        if stream_name == 'stderr':
                            error_parts.append(text)
                        else:
                            output_parts.append(text)
                    
                    elif msg_type == 'execute_result':
                        # 执行结果（如 print 输出）
                        data = content.get('data', {})
                        if 'text/plain' in data:
                            output_parts.append(data['text/plain'])
                        elif 'text/html' in data:
                            output_parts.append(f"[HTML 输出]\n{data['text/html']}")
                        elif 'image/png' in data:
                            output_parts.append("[图像输出]")
                    
                    elif msg_type == 'display_data':
                        # 显示数据（如 matplotlib 图表）
                        data = content.get('data', {})
                        if 'text/plain' in data:
                            output_parts.append(data['text/plain'])
                        elif 'image/png' in data:
                            output_parts.append("[图像输出]")
                    
                    elif msg_type == 'error':
                        # 执行错误
                        error_name = content.get('ename', 'Error')
                        error_value = content.get('evalue', '')
                        error_traceback = content.get('traceback', [])
                        error_parts.append(f"{error_name}: {error_value}")
                        if error_traceback:
                            error_parts.append("\n".join(error_traceback))
                    
                    elif msg_type == 'status':
                        # 执行状态
                        execution_state = content.get('execution_state', '')
                        if execution_state == 'idle':
                            # 执行完成
                            break
                    
                except Exception as e:
                    # 超时或其他错误
                    if "timeout" in str(e).lower():
                        break
                    logger.warning(f"获取执行结果时出错: {e}")
                    break
            
            # 获取执行状态
            status_msg = self._kernel_client.get_shell_msg(timeout=1.0)
            if status_msg and status_msg.get('content', {}).get('status') == 'error':
                error_content = status_msg.get('content', {})
                error_parts.append(
                    f"{error_content.get('ename', 'Error')}: {error_content.get('evalue', '')}"
                )
            
            # 组合输出
            output = "\n".join(output_parts) if output_parts else "代码执行完成（无输出）"
            error = "\n".join(error_parts) if error_parts else None
            
            if error:
                return ToolResult(
                    success=False,
                    error=f"代码执行出错: {error}",
                    data={"output": output, "code": code}
                )
            
            return ToolResult(
                success=True,
                data={
                    "output": output,
                    "code": code,
                    "kernel": kernel_name
                }
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"代码执行超时（{timeout}秒）"
            )
        except Exception as e:
            logger.error(f"Jupyter 代码执行失败: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Jupyter 代码执行失败: {str(e)}"
            )
    
    def __del__(self):
        """清理资源"""
        self._cleanup_kernel()

