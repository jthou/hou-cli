"""流式响应处理器

支持显示调试信息、工具调用和内容
"""
from typing import AsyncIterator
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
import json


class StreamRenderer:
    """流式渲染器，支持显示调试信息和工具调用"""

    def __init__(self, renderer_factory=None):
        # renderer_factory 参数保留以兼容现有代码，但不再使用
        pass

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
        
        # 构建详细信息文本
        detail_text = ""
        if details:
            detail_lines = []
            for k, v in details.items():
                if isinstance(v, (list, dict)):
                    v_str = json.dumps(v, ensure_ascii=False, indent=2)
                else:
                    v_str = str(v)
                detail_lines.append(f"  {k}: {v_str}")
            detail_text = "\n".join(detail_lines)
        
        panel_content = f"[{color}]{message}[/{color}]"
        if detail_text:
            panel_content += f"\n{detail_text}"
        
        console.print(Panel(
            panel_content,
            border_style=color,
            title=f"[{color}]🔍 {category.upper()}[/{color}]",
            padding=(0, 1)
        ))
    
    def _render_tool_info(self, tool_data: dict, console: Console):
        """渲染工具调用信息"""
        tool_name = tool_data.get("name", "unknown")
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
    
    async def render_stream(
        self,
        stream: AsyncIterator[str],
        console: Console,
    ):
        """渲染流式响应（支持调试信息和工具调用）

        Args:
            stream: 流式数据迭代器
            console: Rich Console 实例
        """
        full_content = ""
        buffer = ""
        
        # 使用 Live 组件实时更新，流式显示文本
        try:
            with Live(console=console, refresh_per_second=10) as live:
                async for chunk in stream:
                    try:
                        # 清理无效的 Unicode 字符
                        chunk = self._clean_unicode(chunk)
                        buffer += chunk
                        
                        # 检查是否有完整的行（以 \n 结尾）
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            
                            # 检查是否是调试信息或工具调用信息
                            if line.startswith("__DEBUG__:"):
                                try:
                                    debug_data = json.loads(line[10:])  # 移除 "__DEBUG__:" 前缀
                                    self._render_debug_info(debug_data, console)
                                except (json.JSONDecodeError, KeyError):
                                    # JSON 解析失败，跳过
                                    pass
                            elif line.startswith("__TOOL__:"):
                                try:
                                    tool_data = json.loads(line[9:])  # 移除 "__TOOL__:" 前缀
                                    self._render_tool_info(tool_data, console)
                                except (json.JSONDecodeError, KeyError):
                                    # JSON 解析失败，跳过
                                    pass
                            else:
                                # 普通内容
                                full_content += line + "\n"
                                live.update(full_content)
                        
                        # 如果 buffer 中还有内容但没有换行符，也更新显示
                        if buffer and not buffer.startswith(("__DEBUG__:", "__TOOL__:")):
                            live.update(full_content + buffer)
                    except KeyboardInterrupt:
                        # 用户按 Ctrl+C，终止流式处理
                        raise  # 重新抛出，让外层处理
                    except Exception as chunk_error:
                        # 处理单个 chunk 时出错，记录但继续
                        console.print(f"[dim]处理数据块时出错: {chunk_error}[/dim]")
                        continue
        except KeyboardInterrupt:
            # 用户按 Ctrl+C，显示提示并终止
            console.print("\n[bold yellow]⚠ 对话已终止[/bold yellow]")
            # 显示已收集的内容
            if full_content:
                console.print(full_content)
            raise  # 重新抛出，让调用者知道是用户中断
        except Exception as e:
            # 流式处理失败，显示错误
            console.print(f"\n[bold red]流式处理失败[/bold red]: {e}")
            # 显示已收集的内容
            if full_content:
                console.print(full_content)
        
        # 流式完成后，Live 组件会保留最终内容
        # 不需要额外处理
