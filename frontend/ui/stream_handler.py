"""流式响应处理器

支持显示调试信息、工具调用和内容
"""
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


class StreamRenderer:
    """流式渲染器，支持显示调试信息和工具调用"""

    def __init__(self, renderer_factory=None):
        # renderer_factory 参数保留以兼容现有代码，但不再使用
        self.interactive_executor = None  # 延迟初始化，需要 console

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
        
        # 特殊处理 execute_code 工具的调试信息
        if message == "执行工具" and details.get("name") == "execute_code":
            # 解析 args 参数
            args_str = details.get("args", "")
            try:
                if isinstance(args_str, str):
                    args = json.loads(args_str)
                else:
                    args = args_str
                
                code = args.get("code", "")
                language = args.get("language", "python")
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
        
        # 提取信息
        code = tool_args.get("code", "")
        language = tool_args.get("language", "python")
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
        if tool_name == "execute_code":
            # 如果有执行结果，使用专门的渲染方法
            if tool_data.get("result") is not None or tool_data.get("success") is not False:
                self._render_code_executor(tool_data, console)
                return
            # 如果只是工具调用（还没有结果），也要格式化显示代码
            tool_args = tool_data.get("args", {})
            code = tool_args.get("code", "")
            language = tool_args.get("language", "python")
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
                    # PDF 工具特殊处理
                    if tool_name == "pdf_parser":
                        if "content" in result:
                            content = result.get("content", "")
                            output_path = result.get("output_path", "")
                            backend = result.get("backend", "unknown")
                            content_length = result.get("content_length", 0)
                            
                            content_lines.append(f"\n[bold]后端:[/bold] {backend}")
                            if output_path:
                                content_lines.append(f"[bold]输出文件:[/bold] {output_path}")
                            if content_length:
                                content_lines.append(f"[bold]内容长度:[/bold] {content_length} 字符")
                            
                            # 显示内容预览（前500字符）
                            if content:
                                preview = content[:500] if len(content) > 500 else content
                                content_lines.append(f"\n[bold]内容预览:[/bold]")
                                content_lines.append(f"[dim]{preview}[/dim]")
                                if len(content) > 500:
                                    content_lines.append(f"[dim]... (还有 {len(content) - 500} 字符，请查看输出文件)[/dim]")
                        else:
                            # 其他 PDF 结果格式
                            result_str = json.dumps(result, ensure_ascii=False, indent=2)
                            if len(result_str) > 500:
                                result_str = result_str[:500] + "..."
                            content_lines.append(f"\n[dim]{result_str}[/dim]")
                    # 如果是文件搜索结果，显示摘要
                    elif "summary" in result:
                        content_lines.append(f"\n[dim]{result['summary']}[/dim]")
                    elif "results" in result:
                        count = result.get("count", 0)
                        total = result.get("total", 0)
                        content_lines.append(f"\n[dim]找到 {count}/{total} 个结果[/dim]")
                    else:
                        # 清理不可序列化的对象（如 Panel）
                        cleaned_result = {}
                        for k, v in result.items():
                            if isinstance(v, (str, int, float, bool, type(None))):
                                cleaned_result[k] = v
                            elif isinstance(v, (dict, list)):
                                try:
                                    json.dumps(v, ensure_ascii=False)
                                    cleaned_result[k] = v
                                except (TypeError, ValueError):
                                    cleaned_result[k] = f"[{type(v).__name__}对象]"
                            else:
                                cleaned_result[k] = f"[{type(v).__name__}对象]"
                        
                        result_str = json.dumps(cleaned_result, ensure_ascii=False, indent=2)
                        if len(result_str) > 500:
                            result_str = result_str[:500] + "..."
                        content_lines.append(f"\n[dim]{result_str}[/dim]")
                else:
                    # 非字典结果，清理不可序列化的对象
                    result_str = str(result)
                    # 检查是否是 Panel 对象
                    if "Panel object" in result_str or "<rich.panel.Panel" in result_str:
                        result_str = "[Panel对象，无法直接显示]"
                    if len(result_str) > 500:
                        result_str = result_str[:500] + "..."
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
    
    def _render_progress_info(self, progress_data: dict, console: Console, in_live_context: bool = False):
        """渲染进度信息（多行显示）
        
        Args:
            progress_data: 进度数据，格式：
                {
                    "type": "progress",
                    "category": "tool",
                    "tool_name": "whisper",
                    "message": "转录进行中... 已用时: 00:30"
                }
            console: Rich Console 实例
            in_live_context: 是否在 Live 上下文中（如果在 Live 中，需要返回 Rich Text 对象）
        """
        tool_name = progress_data.get("tool_name", "unknown")
        message = progress_data.get("message", "")
        
        # 根据工具名称选择图标
        tool_icons = {
            "whisper": "🎤",
            "video_downloader": "📥",
            "ffmpeg": "🎬",
            "jupyter": "📓",
        }
        
        icon = tool_icons.get(tool_name, "📊")
        
        # 根据消息类型选择样式
        if "完成" in message:
            # 完成消息，使用绿色
            style = "green"
        elif "错误" in message or "失败" in message:
            # 错误消息，使用红色
            style = "red"
        elif "进行中" in message or "加载" in message or "处理" in message:
            # 进行中消息，使用青色
            style = "cyan"
        else:
            # 默认样式
            style = "dim cyan"
        
        # 先打印一个点（不换行），表示收到了进度消息
        import sys
        sys.stdout.write(".")
        sys.stdout.flush()
        
        # 格式化进度消息（使用 Rich 标记字符串）
        progress_text = f"[{style}]{icon} {tool_name}[/{style}]: {message}\n"
        
        if in_live_context:
            # 在 Live 上下文中，返回格式化的字符串（Rich 标记会被 live.update 正确渲染）
            return progress_text
        else:
            # 不在 Live 上下文中，直接打印
            console.print(progress_text, end="")
            return None
    
    async def render_stream(
        self,
        stream: AsyncIterator[str],
        console: Console,
    ):
        """渲染流式响应（支持调试信息、工具调用和确认请求）

        Args:
            stream: 流式数据迭代器
            console: Rich Console 实例
        """
        full_content = ""
        buffer = ""
        
        # 初始化交互式执行器
        if not self.interactive_executor:
            self.interactive_executor = InteractiveExecutor(console)
        
        # 使用 Live 组件实时更新，流式显示文本
        try:
            with Live(console=console, refresh_per_second=10) as live:
                async for chunk in stream:
                    try:
                        # #region agent log
                        try:
                            import json as json_module
                            with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"stream_handler.py:render_stream","message":"接收chunk","data":{"chunk_type":type(chunk).__name__,"chunk_len":len(str(chunk)) if chunk else 0},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                f.write('\n')
                        except: pass
                        # #endregion
                        # 清理无效的 Unicode 字符
                        chunk = self._clean_unicode(chunk)
                        buffer += chunk
                        
                        # 检查是否有完整的行（以 \n 结尾）
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            
                            # 检查是否是调试信息、工具调用信息或确认请求
                            if line.startswith("__DEBUG__:"):
                                try:
                                    # #region agent log
                                    try:
                                        import json as json_module
                                        with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                            json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"stream_handler.py:render_stream","message":"准备解析DEBUG JSON","data":{"line_len":len(line),"line_preview":line[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                            f.write('\n')
                                    except: pass
                                    # #endregion
                                    json_str = line[10:]  # 移除 "__DEBUG__:" 前缀
                                    # 清理 JSON 字符串中的无效字符
                                    json_str = self._clean_unicode(json_str)
                                    debug_data = json.loads(json_str)
                                    self._render_debug_info(debug_data, console)
                                except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                                    # #region agent log
                                    try:
                                        import json as json_module
                                        with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                            json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"stream_handler.py:render_stream","message":"DEBUG JSON解析失败","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                            f.write('\n')
                                    except: pass
                                    # #endregion
                                    # JSON 解析失败，跳过
                                    pass
                            elif line.startswith("__TOOL__:"):
                                try:
                                    # #region agent log
                                    try:
                                        import json as json_module
                                        with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                            json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"stream_handler.py:render_stream","message":"准备解析TOOL JSON","data":{"line_len":len(line)},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                            f.write('\n')
                                    except: pass
                                    # #endregion
                                    json_str = line[9:]  # 移除 "__TOOL__:" 前缀
                                    # 清理 JSON 字符串中的无效字符
                                    json_str = self._clean_unicode(json_str)
                                    tool_data = json.loads(json_str)
                                    self._render_tool_info(tool_data, console)
                                except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                                    # #region agent log
                                    try:
                                        import json as json_module
                                        try:
                                            error_msg = str(e)[:200]
                                        except:
                                            error_msg = f"{type(e).__name__}: 无法获取错误消息"
                                        with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                            json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"stream_handler.py:render_stream","message":"TOOL JSON解析失败","data":{"error_type":type(e).__name__,"error_msg":error_msg},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                            f.write('\n')
                                    except: pass
                                    # #endregion
                                    # JSON 解析失败，跳过
                                    pass
                            elif line.startswith("__PROGRESS__:"):
                                try:
                                    json_str = line[13:]  # 移除 "__PROGRESS__:" 前缀（13个字符）
                                    # 调试：打印原始 JSON 字符串
                                    import sys
                                    sys.stdout.write(f"\n[DEBUG] ✅ 收到进度消息\n")
                                    sys.stdout.write(f"[DEBUG] 原始行长度: {len(line)}\n")
                                    sys.stdout.write(f"[DEBUG] JSON 字符串长度: {len(json_str)}\n")
                                    sys.stdout.write(f"[DEBUG] JSON 字符串前200字符: {repr(json_str[:200])}\n")
                                    sys.stdout.flush()
                                    # 清理 JSON 字符串中的无效字符
                                    json_str = self._clean_unicode(json_str)
                                    sys.stdout.write(f"[DEBUG] 清理后 JSON 字符串前200字符: {repr(json_str[:200])}\n")
                                    sys.stdout.flush()
                                    progress_data = json.loads(json_str)
                                    sys.stdout.write(f"[DEBUG] ✅ JSON 解析成功: {progress_data}\n")
                                    sys.stdout.flush()
                                    # 渲染进度信息（在 Live 上下文中，返回格式化的字符串）
                                    progress_text = self._render_progress_info(progress_data, console, in_live_context=True)
                                    # 调试：打印 progress_text 内容
                                    sys.stdout.write(f"[DEBUG] progress_text: {repr(progress_text)}\n")
                                    sys.stdout.write(f"[DEBUG] progress_text is None: {progress_text is None}\n")
                                    sys.stdout.write(f"[DEBUG] progress_text length: {len(progress_text) if progress_text else 0}\n")
                                    sys.stdout.flush()
                                    if progress_text:
                                        # 直接添加到 full_content（Rich 标记字符串会被 live.update 正确渲染）
                                        full_content += progress_text
                                        # 使用 Text 对象确保 Rich 标记被正确渲染
                                        live_text = Text.from_markup(full_content) if full_content else Text("")
                                        live.update(live_text)
                                    else:
                                        # 如果没有返回文本，至少打印一个点
                                        sys.stdout.write(".")
                                        sys.stdout.flush()
                                except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                                    # JSON 解析失败，至少打印一个点表示收到了消息
                                    import sys
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    # 调试：打印异常信息
                                    sys.stdout.write(f"\n[DEBUG] 进度消息 JSON 解析失败!\n")
                                    sys.stdout.write(f"[DEBUG] 异常类型: {type(e).__name__}\n")
                                    sys.stdout.write(f"[DEBUG] 异常消息: {str(e)}\n")
                                    sys.stdout.write(f"[DEBUG] 原始数据长度: {len(line)}\n")
                                    sys.stdout.write(f"[DEBUG] 原始数据前100字符: {repr(line[:100])}\n")
                                    sys.stdout.write(f"[DEBUG] 原始数据完整内容: {repr(line)}\n")
                                    sys.stdout.flush()
                                    logger.debug(f"进度消息 JSON 解析失败: {e}, 原始数据: {line[:100]}")
                                    sys.stdout.write(".")
                                    sys.stdout.flush()
                                    pass
                            elif line.startswith("__CONFIRM__:"):
                                try:
                                    # #region agent log
                                    try:
                                        import json as json_module
                                        with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                            json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"stream_handler.py:render_stream","message":"准备解析CONFIRM JSON","data":{"line_len":len(line)},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                            f.write('\n')
                                    except: pass
                                    # #endregion
                                    json_str = line[11:]  # 移除 "__CONFIRM__:" 前缀
                                    # 清理 JSON 字符串中的无效字符
                                    json_str = self._clean_unicode(json_str)
                                    confirm_data = json.loads(json_str)
                                    self._render_confirm_request(confirm_data, console)
                                except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                                    # #region agent log
                                    try:
                                        import json as json_module
                                        try:
                                            error_msg = str(e)[:200]
                                        except:
                                            error_msg = f"{type(e).__name__}: 无法获取错误消息"
                                        with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                            json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"stream_handler.py:render_stream","message":"CONFIRM JSON解析失败","data":{"error_type":type(e).__name__,"error_msg":error_msg},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                            f.write('\n')
                                    except: pass
                                    # #endregion
                                    # JSON 解析失败，跳过
                                    pass
                            else:
                                # 普通内容
                                full_content += line + "\n"
                                live.update(full_content)
                        
                        # 如果 buffer 中还有内容但没有换行符，也更新显示
                        if buffer and not buffer.startswith(("__DEBUG__:", "__TOOL__:", "__CONFIRM__:", "__PROGRESS__:")):
                            # 使用 Text 对象确保 Rich 标记被正确渲染
                            live_text = Text.from_markup(full_content + buffer) if (full_content + buffer) else Text("")
                            live.update(live_text)
                    except KeyboardInterrupt:
                        # 用户按 Ctrl+C，终止流式处理
                        raise  # 重新抛出，让外层处理
                    except Exception as chunk_error:
                        # 处理单个 chunk 时出错，记录但继续
                        # #region agent log
                        try:
                            import json as json_module
                            with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"H","location":"stream_handler.py:render_stream","message":"chunk处理异常","data":{"error_type":type(chunk_error).__name__},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                f.write('\n')
                        except: pass
                        # #endregion
                        # 安全地获取错误消息
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
                import json as json_module
                with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"H","location":"stream_handler.py:render_stream","message":"流式处理异常","data":{"error_type":type(e).__name__},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                    f.write('\n')
            except: pass
            # #endregion
            # 流式处理失败，显示错误
            # 安全地获取错误消息
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
        
        # 流式完成后，Live 组件会保留最终内容
        # 不需要额外处理
