"""流式响应处理器

支持显示调试信息、工具调用和内容
"""
from pathlib import Path
from typing import AsyncIterator, List
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich.markdown import Markdown
from rich.columns import Columns
from rich.align import Align
import rich.box
import json
from frontend.ui.interactive_executor import InteractiveExecutor
from frontend.client.message_handler import MessageHandler

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class StreamRenderer:
    """流式渲染器，支持显示调试信息和工具调用"""

    def __init__(self, renderer_factory=None):
        # renderer_factory 参数保留以兼容现有代码，但不再使用
        self.interactive_executor = None  # 延迟初始化，需要 console
        self.current_status_line = None  # 当前状态行内容（用于同一行更新）

    def _clean_unicode(self, text: str) -> str:
        """
        清理无效的 Unicode 字符（代理对）
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        try:
            # 尝试编码为 UTF-8，如果失败则替换无效字符
            return text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
        except Exception:
            # 如果仍然失败，使用 replace 策略
            return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    
    def _render_debug_info(self, debug_data: dict, console: Console):
        """渲染调试信息"""
        category = debug_data.get("category", "unknown")
        message = debug_data.get("message", "")
        details = debug_data.get("details", {})
        
        # 根据类别选择颜色
        color_map = {
            "orchestrator": "cyan",
            "context": "blue",
            "tool": "yellow",
            "llm": "magenta"
        }
        color = color_map.get(category, "dim")
        
        # 特殊处理 exec_py/exec_shell 工具的调试信息
        if message == "执行工具" and details.get("name") in ("exec_py", "exec_shell"):
            # 解析 args 参数
            args_str = details.get("args", "")
            try:
                if isinstance(args_str, str):
                    args = json.loads(args_str)
                else:
                    args = args_str
                
                code = args.get("code", "")
                language = "python" if details.get("name") == "exec_py" else "zsh"
                explanation = args.get("explanation", "")
                
                # 语言图标和颜色映射
                language_config = {
                    "python": {"icon": "🐍", "color": "yellow"},
                    "bash": {"icon": "💻", "color": "green"},
                    "zsh": {"icon": "💻", "color": "green"},
                    "powershell": {"icon": "⚡", "color": "blue"},
                    "batch": {"icon": "📜", "color": "cyan"}
                }
                lang_config = language_config.get(language, {"icon": "🔧", "color": "white"})
                icon = lang_config["icon"]
                lang_color = lang_config["color"]
                
                # 构建内容
                content_parts: List = []
                content_parts.append(Text(message, style="bold"))
                content_parts.append("")
                
                # 代码部分（带语法高亮）
                if code:
                    code_syntax = Syntax(
                        code,
                        language,
                        theme="monokai",
                        line_numbers=False,
                        word_wrap=True
                    )
                    content_parts.append(Text("📝 代码:", style="bold"))
                    content_parts.append("")
                    content_parts.append(code_syntax)
                    content_parts.append("")
                
                # 说明
                if explanation:
                    content_parts.append(Text(f"💡 说明: {explanation}", style="dim"))
                
                # 渲染面板（优化标题）
                title = Text.assemble(
                    (f"🔍 {category.upper()}", f"bold {color}"),
                    " - ",
                    (f"{icon} {language.upper()}", f"bold {lang_color}")
                )
                console.print(Panel(
                    Group(*content_parts),
                    border_style=color,
                    title=title,
                    padding=(1, 1),
                    box=rich.box.ROUNDED
                ))
                return
            except (json.JSONDecodeError, KeyError, AttributeError):
                # 解析失败，使用默认显示
                pass
        
        # 默认处理：构建详细信息文本
        detail_text = ""
        if details:
            detail_lines = []
            for k, v in details.items():
                if isinstance(v, (list, dict)):
                    v_str = json.dumps(v, ensure_ascii=False, indent=2)
                elif isinstance(v, str) and len(v) > 200:
                    # 长字符串截断
                    v_str = v[:200] + "..."
                else:
                    v_str = str(v)
                detail_lines.append(f"  {k}: {v_str}")
            detail_text = "\n".join(detail_lines)
        
        panel_content = message
        if detail_text:
            panel_content += f"\n{detail_text}"
        
        console.print(Panel(
            panel_content,
            border_style=color,
            title=f"[{color}]🔍 {category.upper()}[/{color}]",
            padding=(0, 1)
        ))
    
    def _render_code_executor(self, tool_data: dict, console: Console):
        """专门渲染代码执行工具的结果"""
        tool_args = tool_data.get("args", {})
        result = tool_data.get("result", {})
        success = tool_data.get("success", False)
        error = tool_data.get("error")
        tool_name = tool_data.get("name", "")
        
        # 提取信息（exec_py/exec_shell 无 language 参数，从工具名推断）
        code = tool_args.get("code", "")
        language = tool_args.get("language") or ("python" if tool_name == "exec_py" else "zsh")
        explanation = tool_args.get("explanation", "")
        output = result.get("output", "") if result else ""
        error_output = result.get("error", "") if result else ""
        exit_code = result.get("exit_code", 0) if result else 0
        execution_time = result.get("execution_time", 0) if result else 0
        memory_used = result.get("memory_used", 0) if result else 0
        
        # 语言图标和颜色映射
        language_config = {
            "python": {"icon": "🐍", "color": "yellow"},
            "bash": {"icon": "💻", "color": "green"},
            "zsh": {"icon": "💻", "color": "green"},
            "powershell": {"icon": "⚡", "color": "blue"},
            "batch": {"icon": "📜", "color": "cyan"}
        }
        lang_config = language_config.get(language, {"icon": "🔧", "color": "white"})
        icon = lang_config["icon"]
        lang_color = lang_config["color"]
        
        # 构建内容（优化布局）
        content_parts: List = []
        
        # 代码部分（使用更紧凑的布局）
        if code:
            # 代码标题和内容
            code_header = Text.assemble(
                ("📝 ", "bold"),
                ("代码", "bold cyan"),
                (f" ({language})", "dim")
            )
            content_parts.append(code_header)
            content_parts.append("")
            
            # 代码内容（带边框）
            code_panel = Panel(
                Syntax(
                    code,
                    language,
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True
                ),
                border_style="dim",
                padding=(0, 1),
                box=rich.box.SQUARE
            )
            content_parts.append(code_panel)
            content_parts.append("")
        
        # 执行状态（使用更醒目的显示）
        if success:
            status_text = Text.assemble(
                ("✅ ", "bold green"),
                ("执行成功", "bold green")
            )
        else:
            status_text = Text.assemble(
                ("❌ ", "bold red"),
                ("执行失败", "bold red"),
                (f" (退出码: {exit_code})", "dim red")
            )
        content_parts.append(status_text)
        content_parts.append("")
        
        # 输出部分（支持折叠）
        if output:
            MAX_OUTPUT_LINES = 30  # 减少默认显示行数，更紧凑
            lines = output.split('\n')
            is_truncated = len(lines) > MAX_OUTPUT_LINES
            
            if is_truncated:
                display_lines = lines[:MAX_OUTPUT_LINES]
                display_output = '\n'.join(display_lines)
                truncate_info = f"\n\n[dim]... (输出已截断，共 {len(lines)} 行，显示前 {MAX_OUTPUT_LINES} 行)[/dim]"
                display_output += truncate_info
            else:
                display_output = output
            
            # 输出标题
            output_header = Text.assemble(
                ("📤 ", "bold"),
                ("输出", "bold cyan"),
                (f" ({len(lines)} 行)" if not is_truncated else f" (共 {len(lines)} 行，显示前 {MAX_OUTPUT_LINES} 行)", "dim")
            )
            content_parts.append(output_header)
            content_parts.append("")
            
            # 输出内容（使用更紧凑的显示）
            if is_truncated:
                output_panel = Panel(
                    display_output,
                    border_style="blue",
                    padding=(0, 1),
                    box=rich.box.SQUARE,
                    title="[dim]💡 提示: 输出已截断，完整输出请查看日志[/dim]"
                )
            else:
                output_panel = Panel(
                    display_output,
                    border_style="blue",
                    padding=(0, 1),
                    box=rich.box.SQUARE
                )
            content_parts.append(output_panel)
            content_parts.append("")
        
        # 错误部分（优化显示）
        if error_output or error:
            error_content = error_output or error
            # 错误信息也截断
            MAX_ERROR_LINES = 30
            error_lines = error_content.split('\n')
            is_error_truncated = len(error_lines) > MAX_ERROR_LINES
            
            if is_error_truncated:
                display_error_lines = error_lines[:MAX_ERROR_LINES]
                display_error = '\n'.join(display_error_lines)
                display_error += f"\n\n[dim]... (错误信息已截断，共 {len(error_lines)} 行，显示前 {MAX_ERROR_LINES} 行)[/dim]"
            else:
                display_error = error_content
            
            # 错误标题
            error_header = Text.assemble(
                ("⚠️  ", "bold red"),
                ("错误", "bold red"),
                (f" ({len(error_lines)} 行)" if not is_error_truncated else f" (共 {len(error_lines)} 行，显示前 {MAX_ERROR_LINES} 行)", "dim red")
            )
            content_parts.append(error_header)
            content_parts.append("")
            
            # 尝试检测是否是 Python traceback，使用语法高亮
            if "Traceback" in error_content or "File \"" in error_content:
                # 使用 Syntax 高亮显示错误
                error_syntax = Syntax(
                    display_error,
                    "python",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True
                )
                error_panel = Panel(
                    error_syntax,
                    border_style="red",
                    padding=(0, 1),
                    box=rich.box.SQUARE
                )
                content_parts.append(error_panel)
            else:
                error_panel = Panel(
                    display_error,
                    border_style="red",
                    padding=(0, 1),
                    box=rich.box.SQUARE
                )
                content_parts.append(error_panel)
            content_parts.append("")
        
        # 统计信息（使用表格显示，更美观）
        if execution_time > 0 or memory_used > 0:
            stats_table = Table.grid(padding=(0, 2), expand=False)
            stats_table.add_column(style="dim", width=12)
            stats_table.add_column(style="cyan")
            
            if execution_time > 0:
                stats_table.add_row("⏱️  执行时间", f"{execution_time:.3f} 秒")
            if memory_used > 0:
                stats_table.add_row("💾 内存使用", f"{memory_used:.2f} MB")
            
            content_parts.append("")
            content_parts.append(stats_table)
        
        # 渲染面板（优化标题和边框颜色）
        title_parts = [f"{icon} ", Text(f"代码执行: {language.upper()}", style=f"bold {lang_color}")]
        if explanation:
            title_parts.append(Text(f" - {explanation}", style="dim"))
        
        border_color = "green" if success else "red"
        title = Text.assemble(*title_parts)
        
        console.print(Panel(
            Group(*content_parts),
            border_style=border_color,
            title=title,
            padding=(1, 1),
            box=rich.box.ROUNDED if success else rich.box.DOUBLE  # 成功用圆角，失败用双线
        ))
    
    def _render_tool_info(self, tool_data: dict, console: Console):
        """渲染工具调用信息"""
        tool_name = tool_data.get("name", "unknown")
        
        # 特殊处理代码执行工具
        if tool_name in ("exec_py", "exec_shell"):
            # 如果有执行结果，使用专门的渲染方法
            if tool_data.get("result") is not None or tool_data.get("success") is not False:
                self._render_code_executor(tool_data, console)
                return
            # 如果只是工具调用（还没有结果），也要格式化显示代码
            tool_args = tool_data.get("args", {})
            code = tool_args.get("code", "")
            language = "python" if tool_name == "exec_py" else "zsh"
            explanation = tool_args.get("explanation", "")
            
            # 语言图标映射
            language_icons = {
                "python": "🐍",
                "bash": "💻",
                "zsh": "💻",
                "powershell": "⚡",
                "batch": "📜"
            }
            icon = language_icons.get(language, "🔧")
            
            # 构建内容
            content_parts: List = []
            
            # 代码部分（带语法高亮）
            if code:
                code_syntax = Syntax(
                    code,
                    language,
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True
                )
                content_parts.append(Text("📝 代码:", style="bold"))
                content_parts.append("")
                content_parts.append(code_syntax)
                content_parts.append("")
            
            # 说明
            if explanation:
                content_parts.append(Text(f"💡 说明: {explanation}", style="dim"))
                content_parts.append("")
            
            # 渲染面板
            title = f"{icon} 代码执行: {language.upper()}"
            console.print(Panel(
                Group(*content_parts),
                border_style="yellow",
                title=title,
                padding=(1, 1)
            ))
            return
        
        # 其他工具使用原有逻辑
        tool_args = tool_data.get("args", {})
        success = tool_data.get("success", False)
        result = tool_data.get("result")
        error = tool_data.get("error")
        
        # 构建工具信息面板
        content_lines = [
            f"[bold]工具:[/bold] {tool_name}",
            ""
        ]
        
        # 参数
        if tool_args:
            content_lines.append("[bold]参数:[/bold]")
            args_str = json.dumps(tool_args, ensure_ascii=False, indent=2)
            content_lines.append(f"[dim]{args_str}[/dim]")
            content_lines.append("")
        
        # 结果
        if success:
            content_lines.append("[green]✓ 执行成功[/green]")
            if result:
                # 格式化结果
                if isinstance(result, dict):
                    # 如果是文件搜索结果，显示摘要
                    if "summary" in result:
                        content_lines.append(f"\n[dim]{result['summary']}[/dim]")
                    elif "results" in result:
                        count = result.get("count", 0)
                        total = result.get("total", 0)
                        content_lines.append(f"\n[dim]找到 {count}/{total} 个结果[/dim]")
                    else:
                        result_str = json.dumps(result, ensure_ascii=False, indent=2)
                        if len(result_str) > 200:
                            result_str = result_str[:200] + "..."
                        content_lines.append(f"\n[dim]{result_str}[/dim]")
                else:
                    result_str = str(result)
                    if len(result_str) > 200:
                        result_str = result_str[:200] + "..."
                    content_lines.append(f"\n[dim]{result_str}[/dim]")
        else:
            content_lines.append(f"[red]✗ 执行失败[/red]")
            if error:
                content_lines.append(f"\n[red]{error}[/red]")
        
        console.print(Panel(
            "\n".join(content_lines),
            border_style="yellow" if success else "red",
            title=f"[yellow]🔧 TOOL: {tool_name}[/yellow]",
            padding=(1, 1)
        ))
    
    def _render_confirm_request(self, confirm_data: dict, console: Console):
        """渲染确认请求"""
        if not self.interactive_executor:
            self.interactive_executor = InteractiveExecutor(console)
        
        code = confirm_data.get("code", "")
        risk_level = confirm_data.get("risk_level", "")
        reason = confirm_data.get("reason", "")
        
        # 请求用户确认
        from frontend.ui.interactive_executor import ConfirmationResult
        result = self.interactive_executor.request_confirmation(
            code=code,
            risk_level=risk_level,
            reason=reason
        )
        
        # 显示确认结果
        if result.approved:
            console.print("[green]✓ 用户已批准执行[/green]")
            # TODO: 将确认结果返回给后端（需要实现确认结果传递机制）
        else:
            console.print("[red]✗ 用户已取消执行[/red]")
    
    def _render_evaluation_info(self, evaluation_data: dict, console: Console):
        """渲染对话评估结果"""
        evaluation = evaluation_data.get("evaluation", {})
        if not evaluation:
            return
        
        overall_score = evaluation.get("overall_score", 0)
        dimension_scores = evaluation.get("dimension_scores", {})
        evaluation_text = evaluation.get("evaluation", "")
        
        # 根据分数选择颜色
        if overall_score >= 90:
            score_color = "green"
            score_emoji = "⭐"
        elif overall_score >= 80:
            score_color = "cyan"
            score_emoji = "✓"
        elif overall_score >= 70:
            score_color = "yellow"
            score_emoji = "⚠"
        else:
            score_color = "red"
            score_emoji = "✗"
        
        # 构建内容
        content_parts: List = []
        
        # 总体分数
        score_text = Text.assemble(
            (f"{score_emoji} 总体分数: ", "bold"),
            (f"{overall_score}/100", f"bold {score_color}")
        )
        content_parts.append(score_text)
        content_parts.append("")
        
        # 各维度分数
        if dimension_scores:
            content_parts.append(Text("各维度分数：", style="bold"))
            dimension_names = {
                "relevance": "相关性",
                "accuracy": "准确性",
                "helpfulness": "有用性",
                "completeness": "完整性",
                "clarity": "清晰度"
            }
            for dim_id, score in dimension_scores.items():
                dim_name = dimension_names.get(dim_id, dim_id)
                dim_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
                dim_text = Text.assemble(
                    (f"  • {dim_name}: ", "dim"),
                    (f"{score}/100", f"bold {dim_color}")
                )
                content_parts.append(dim_text)
            content_parts.append("")
        
        # 评估说明
        if evaluation_text:
            content_parts.append(Text("评估说明：", style="bold"))
            content_parts.append(Text(evaluation_text, style="dim"))
        
        # 渲染面板
        title = Text.assemble(
            ("📊 ", "bold"),
            ("对话评估", f"bold {score_color}")
        )
        console.print(Panel(
            Group(*content_parts),
            border_style=score_color,
            title=title,
            padding=(1, 1),
            box=rich.box.ROUNDED
        ))
    
    def _render_status_info(self, status_data: dict, console: Console, inline: bool = True):
        """渲染状态更新信息（用于长任务）
        
        Args:
            status_data: 状态数据字典
            console: Rich Console 实例
            inline: 是否在同一行显示（默认 True）
        """
        task = status_data.get("task", "未知任务")
        progress = status_data.get("progress", 0)
        message = status_data.get("message", "处理中...")
        elapsed_time = status_data.get("elapsed_time", 0)
        estimated_remaining = status_data.get("estimated_remaining")
        
        # 格式化时间
        def format_time(seconds):
            if seconds < 60:
                return f"{int(seconds)}秒"
            elif seconds < 3600:
                return f"{int(seconds // 60)}分{int(seconds % 60)}秒"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}小时{minutes}分"
        
        if inline:
            # 同一行显示（使用 \r 回车符）
            # 构建状态行文本
            status_parts = []
            status_parts.append(f"[cyan]📊 {task}[/cyan]")
            
            if progress > 0:
                # 简化的进度条（更短）
                bar_length = 20
                filled = int(progress * bar_length / 100)
                progress_bar = "█" * filled + "░" * (bar_length - filled)
                status_parts.append(f"[cyan][{progress_bar}] {progress}%[/cyan]")
            
            status_parts.append(f"[dim]{message}[/dim]")
            status_parts.append(f"[dim]⏱️ {format_time(elapsed_time)}[/dim]")
            
            if estimated_remaining is not None:
                status_parts.append(f"[dim]⏳ {format_time(estimated_remaining)}[/dim]")
            
            status_line = " | ".join(status_parts)
            # 使用 \r 在同一行更新，并清除到行尾
            console.print(f"\r{status_line}", end="", overflow="ignore")
        else:
            # 多行显示（原有方式，用于详细状态）
            content_parts: List = []
            content_parts.append(Text(f"📊 任务: {task}", style="bold"))
            content_parts.append("")
            
            # 进度条
            progress_bar = "█" * int(progress // 2) + "░" * (50 - int(progress // 2))
            content_parts.append(Text(f"进度: [{progress_bar}] {progress}%", style="cyan"))
            content_parts.append("")
            
            # 状态消息
            content_parts.append(Text(f"状态: {message}", style="dim"))
            content_parts.append("")
            
            # 时间信息
            time_info = f"已用时间: {format_time(elapsed_time)}"
            if estimated_remaining is not None:
                time_info += f" | 预计剩余: {format_time(estimated_remaining)}"
            content_parts.append(Text(time_info, style="dim"))
            
            # 渲染面板
            console.print(Panel(
                Group(*content_parts),
                border_style="blue",
                title="[blue]📊 任务状态[/blue]",
                padding=(1, 1),
                box=rich.box.ROUNDED
            ))
    
    async def render_stream(
        self,
        stream: AsyncIterator[str],
        console: Console,
    ):
        import json
        import time
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_handler.py:render_stream:entry","message":"render_stream被调用","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        """渲染流式响应（支持调试信息、工具调用和确认请求）

        Args:
            stream: 流式数据迭代器
            console: Rich Console 实例
        """
        full_content = ""
        buffer = ""
        tool_streaming = ""  # 工具执行时的流式输出（exec_py/exec_shell）

        # 初始化交互式执行器
        if not self.interactive_executor:
            self.interactive_executor = InteractiveExecutor(console)
        
        # 使用 Live 组件实时更新，流式显示文本
        # 状态行内容（用于在同一行更新）- 必须在with语句外初始化
        status_display = None
        
        try:
            # #region agent log
            try:
                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_handler.py:render_stream:before_Live","message":"准备创建Live组件","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    f.flush()
            except: pass
            # #endregion
            
            with Live(console=console, refresh_per_second=10) as live:
                # #region agent log
                try:
                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_handler.py:render_stream:before_async_for","message":"准备进入stream循环","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                        f.flush()
                except: pass
                # #endregion
                
                chunk_count = 0
                async for chunk in stream:
                    chunk_count += 1
                    # #region agent log
                    if chunk_count <= 3:  # 只记录前3个chunk
                        try:
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"stream_handler.py:render_stream:received_chunk","message":"render_stream收到chunk","data":{"chunk_count":chunk_count,"chunk_preview":chunk[:50] if chunk else None},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                    # #endregion
                    try:
                        # 使用 MessageHandler 解析消息
                        messages, buffer = MessageHandler.parse_chunk(chunk, buffer)
                        
                        # 处理解析后的消息
                        for msg in messages:
                            msg_type = msg.get("type")
                            msg_data = msg.get("data")
                            
                            if msg_type == "debug":
                                self._render_debug_info(msg_data, console)
                            elif msg_type == "tool":
                                self._render_tool_info(msg_data, console)
                            elif msg_type == "confirm":
                                self._render_confirm_request(msg_data, console)
                            elif msg_type == "evaluation":
                                self._render_evaluation_info(msg_data, console)
                            elif msg_type == "progress":
                                msg_text = msg_data.get("message", "")
                                if msg_text:
                                    tool_streaming += msg_text
                                    display_content = full_content
                                    if tool_streaming:
                                        display_content += "\n[dim]" + tool_streaming.replace("\n", "\n  ") + "[/dim]"
                                    if status_display:
                                        display_content += "\n" + status_display
                                    live.update(display_content)
                            elif msg_type == "tool":
                                tool_streaming = ""  # 工具完成，清空流式缓冲
                                self._render_tool_info(msg_data, console)
                            elif msg_type == "status":
                                # 状态更新：在同一行显示（不换行）
                                # 简化显示：直接显示后端发送的消息
                                message = msg_data.get("message", "处理中...")
                                task = msg_data.get("task", "")
                                elapsed_time = msg_data.get("elapsed_time", 0)
                                
                                # 格式化时间
                                def format_time(seconds):
                                    if seconds < 60:
                                        return f"{int(seconds)}秒"
                                    elif seconds < 3600:
                                        return f"{int(seconds // 60)}分{int(seconds % 60)}秒"
                                    else:
                                        hours = int(seconds // 3600)
                                        minutes = int((seconds % 3600) // 60)
                                        return f"{hours}小时{minutes}分"
                                
                                # 构建简单的状态行
                                status_parts = []
                                if task:
                                    status_parts.append(f"[cyan]{task}[/cyan]")
                                status_parts.append(f"[dim]{message}[/dim]")
                                if elapsed_time > 0:
                                    status_parts.append(f"[dim]⏱️ {format_time(elapsed_time)}[/dim]")
                                
                                status_display = " | ".join(status_parts) if status_parts else message
                                # 更新 Live 组件：将状态行和内容合并显示
                                display_content = full_content
                                if status_display:
                                    display_content = f"{full_content}\n{status_display}"
                                live.update(display_content)
                                # 更新当前状态行内容
                                self.current_status_line = msg_data
                            elif msg_type == "content":
                                # 普通内容
                                # 如果有状态行，先将其添加到内容中（结束状态行）
                                if status_display:
                                    full_content += "\n"  # 换行，结束状态行
                                    status_display = None
                                    self.current_status_line = None
                                full_content += msg_data + "\n"
                                live.update(full_content)
                        
                        # 如果 buffer 中还有内容但没有换行符，也更新显示
                        if buffer and not buffer.startswith(("__DEBUG__:", "__TOOL__:", "__CONFIRM__:", "__EVALUATION__:", "__STATUS__:", "__PROGRESS__:")):
                            display_content = full_content + buffer
                            if status_display:
                                display_content = f"{display_content}\n{status_display}"
                            live.update(display_content)
                    except KeyboardInterrupt:
                        # 用户按 Ctrl+C，终止流式处理
                        raise  # 重新抛出，让外层处理
                    except Exception as chunk_error:
                        # 处理单个 chunk 时出错，记录但继续
                        # #region agent log
                        try:
                            import json
                            import time
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"stream_handler.py:render_stream:chunk_error","message":"处理chunk时出错","data":{"error_type":type(chunk_error).__name__,"error_msg":str(chunk_error)[:500],"error_repr":repr(chunk_error)[:500]},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                        # #endregion
                        try:
                            error_msg = str(chunk_error)
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            error_msg = f"{type(chunk_error).__name__}: 编码错误"
                        except Exception:
                            error_msg = f"{type(chunk_error).__name__}: 无法获取错误消息"
                        console.print(f"[dim]处理数据块时出错: {error_msg}[/dim]")
                        continue
        except KeyboardInterrupt:
            # 用户按 Ctrl+C，显示提示并终止
            console.print("\n[bold yellow]⚠ 对话已终止[/bold yellow]")
            # 显示已收集的内容
            if full_content:
                console.print(full_content)
            raise  # 重新抛出，让调用者知道是用户中断
        except Exception as e:
            # #region agent log
            try:
                import json
                import time
                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"stream_handler.py:render_stream:exception","message":"render_stream异常","data":{"error_type":type(e).__name__,"error_msg":str(e)[:500],"error_repr":repr(e)[:500],"is_panel":hasattr(e,'__class__') and 'Panel' in str(type(e))},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    f.flush()
            except: pass
            # #endregion
            # 流式处理失败，显示错误
            # 确保异常对象不是 Panel
            if hasattr(e, '__class__') and 'Panel' in str(type(e)):
                # 如果是 Panel 对象，提取错误信息
                try:
                    error_msg = f"Panel对象异常: {str(e)}"
                except:
                    error_msg = f"Panel对象异常: {type(e).__name__}"
                e = Exception(error_msg)
            
            try:
                error_msg = str(e)
            except (UnicodeDecodeError, UnicodeEncodeError):
                error_msg = f"{type(e).__name__}: 编码错误"
            except Exception:
                error_msg = f"{type(e).__name__}: 无法获取错误消息"
            console.print(f"\n[bold red]流式处理失败[/bold red]: {error_msg}")
            # 显示已收集的内容
            if full_content:
                console.print(full_content)
            # 重新抛出异常，让外层处理
            raise
        
        # 流式完成后，Live 组件会保留最终内容
        # 不需要额外处理
