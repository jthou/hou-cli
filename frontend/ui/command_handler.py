"""命令处理器（类似 Cursor Agent 的命令模式）"""
from typing import List, Dict, Any, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
import rich.box


class CommandHandler:
    """命令处理器"""
    
    def __init__(self, client=None, current_session_id: Optional[str] = None):
        self.client = client
        self.current_session_id = current_session_id
        self.console = Console()
        
        # 上下文管理子命令
        self.context_commands = {
            "list": ("列出最近的会话", "[limit]"),
            "search": ("搜索包含关键词的会话", "<keyword> [limit]"),
            "restore": ("恢复会话（继续对话）", "[session_id]"),
            "show": ("显示会话详情", "<session_id>"),
            "delete": ("删除指定会话", "<session_id>"),
            "summary": ("生成并显示会话摘要", "<session_id>"),
            "clear": ("清除当前会话的所有消息", ""),
            "switch": ("切换到指定会话", "<session_id>"),
        }
        
        # 顶级命令
        self.top_level_commands = {
            "context": ("上下文管理", "管理会话和上下文"),
            "help": ("显示帮助信息", "[command]"),
            "gvim": ("打开文件或 MediaWiki 页面", "[file_path|mediawiki_page] [options]"),
            "exit": ("退出程序", ""),
            "quit": ("退出程序", ""),
        }
    
    def handle_command(self, input_text: str) -> Tuple[Optional[str], Optional[str]]:
        """处理命令输入
        
        Returns:
            (结果字符串, 新的会话ID) - 如果处理了命令，返回结果字符串和可选的会话ID；如果不是命令，返回 (None, None)
        """
        if not input_text.startswith('/'):
            return (None, None)  # 不是命令
        
        # 解析命令
        parts = input_text[1:].strip().split()
        if not parts:
            # 单独的 '/'，显示命令提示
            return (self._show_command_hint(), None)
        
        command = parts[0].lower()
        args = parts[1:]
        
        # 处理顶级命令
        if command == 'context':
            # /context 子命令
            if not args:
                # /context 单独输入，显示上下文命令帮助
                return (self._show_context_help(), None)
            
            subcommand = args[0].lower()
            sub_args = args[1:]
            
            # 处理 help 子命令
            if subcommand == 'help':
                return (self._show_context_help(), None)
            
            # 上下文管理子命令处理器
            context_handlers = {
                'list': self._handle_list,
                'search': self._handle_search,
                'restore': self._handle_restore,
                'show': self._handle_show,
                'delete': self._handle_delete,
                'summary': self._handle_summary,
                'clear': self._handle_clear,
                'switch': self._handle_switch,
            }
            
            handler = context_handlers.get(subcommand)
            if handler:
                try:
                    result = handler(sub_args)
                    # 如果返回的是元组 (message, session_id)，直接返回
                    if isinstance(result, tuple) and len(result) == 2:
                        return result
                    # 否则返回 (message, None)
                    return (result, None)
                except Exception as e:
                    error_panel = Panel(
                        Text.assemble(
                            ("❌ 执行失败: ", "bold red"),
                            str(e),
                            "\n\n",
                            ("💡 提示: ", "bold cyan"),
                            "请检查命令参数是否正确，或输入 ",
                            ("/help", "bold"),
                            " 查看帮助"
                        ),
                        border_style="red",
                        title="[bold red]⚠️  错误[/bold red]",
                        padding=(1, 2),
                        box=rich.box.ROUNDED
                    )
                    return (str(error_panel), None)
            else:
                error_panel = Panel(
                    Text.assemble(
                        (f"❌ 未知的上下文命令: ", "bold red"),
                        (f"/context {subcommand}", "bold yellow"),
                        "\n\n",
                        ("💡 提示: ", "bold cyan"),
                        "输入 ",
                        ("/context help", "bold"),
                        " 查看所有上下文管理命令"
                    ),
                    border_style="yellow",
                    title="[bold yellow]⚠️  提示[/bold yellow]",
                    padding=(1, 2),
                    box=rich.box.ROUNDED
                )
                return (str(error_panel), None)
        
        elif command == 'help':
            # /help 命令
            return (self._handle_help(args), None)
        
        elif command == 'gvim':
            # /gvim 命令
            return (self._handle_gvim(args), None)
        
        elif command in ['exit', 'quit']:
            # /exit 或 /quit 命令
            return ("[dim]再见！[/dim]", None)
        
        else:
            # 未知命令，提供友好的错误提示
            error_panel = Panel(
                Text.assemble(
                    (f"❌ 未知命令: ", "bold red"),
                    (f"/{command}", "bold yellow"),
                    "\n\n",
                    ("💡 提示: ", "bold cyan"),
                    "输入 ",
                    ("/help", "bold"),
                    " 查看所有可用命令"
                ),
                border_style="red",
                title="[bold red]⚠️  错误[/bold red]",
                padding=(1, 2),
                box=rich.box.ROUNDED
            )
            return (str(error_panel), None)
    
    def _show_command_hint(self) -> str:
        """显示命令提示菜单（优化版）"""
        # 使用表格显示命令，更清晰
        commands_table = Table.grid(padding=(0, 2), expand=False)
        commands_table.add_column(style="cyan bold", width=20)
        commands_table.add_column(style="white", width=50)
        
        # 显示顶级命令
        for cmd, (desc, _) in self.top_level_commands.items():
            commands_table.add_row(f"/{cmd}", desc)
        
        # 构建内容
        content_parts = []
        content_parts.append(Text("📋 可用命令", style="bold cyan"))
        content_parts.append("")
        content_parts.append(commands_table)
        
        # 如果是 context 命令，显示子命令
        content_parts.append("")
        content_parts.append(Text("📁 上下文管理子命令", style="bold yellow"))
        content_parts.append("")
        context_table = Table.grid(padding=(0, 2), expand=False)
        context_table.add_column(style="yellow", width=25)
        context_table.add_column(style="white", width=45)
        for sub_cmd, (sub_desc, sub_args) in self.context_commands.items():
            cmd_str = f"/context {sub_cmd}"
            if sub_args:
                cmd_str += f" {sub_args}"
            context_table.add_row(cmd_str, sub_desc)
        content_parts.append(context_table)
        
        # 显示可用工具（使用表格）
        content_parts.append("")
        content_parts.append(Text("🛠️  可用工具", style="bold green"))
        content_parts.append("")
        try:
            if self.client:
                tools = self.client.list_tools()
                if tools:
                    tools_table = Table.grid(padding=(0, 2), expand=False)
                    tools_table.add_column(style="green", width=20)
                    tools_table.add_column(style="dim", width=50)
                    for tool in tools:
                        tool_name = tool.get("name", "unknown")
                        tool_desc = tool.get("description", "")
                        # 截断描述（取第一行或前 50 个字符）
                        if tool_desc:
                            first_line = tool_desc.split('\n')[0]
                            if len(first_line) > 50:
                                tool_desc = first_line[:50] + "..."
                            else:
                                tool_desc = first_line
                        tools_table.add_row(f"• {tool_name}", tool_desc or "[dim]无描述[/dim]")
                    content_parts.append(tools_table)
                else:
                    content_parts.append(Text("  [dim]暂无可用工具[/dim]"))
            else:
                content_parts.append(Text("  [dim]无法获取工具列表（客户端未初始化）[/dim]"))
        except Exception as e:
            content_parts.append(Text(f"  [dim]无法获取工具列表: {str(e)[:50]}...[/dim]"))
        
        content_parts.append("")
        content_parts.append(Text("💡 提示: 输入 /help 查看详细帮助", style="dim"))
        
        return Panel(
            Group(*content_parts),
            border_style="cyan",
            title="[bold cyan]📖 命令提示[/bold cyan]",
            padding=(1, 2),
            box=rich.box.ROUNDED
        )
    
    def _show_context_help(self) -> str:
        """显示上下文管理命令帮助"""
        hint_text = Text()
        hint_text.append("上下文管理命令:\n")
        
        for cmd, (desc, args) in self.context_commands.items():
            cmd_line = f"  /context {cmd}"
            if args:
                cmd_line += f" {args}"
            cmd_line += f" - {desc}\n"
            hint_text.append(cmd_line)
        
        hint_text.append("\n提示: 输入 /context <command> 执行命令，或 /context help 查看此帮助")
        
        return Panel(
            hint_text,
            border_style="dim",
            title="上下文管理",
            padding=(1, 2)
        )
    
    def _handle_list(self, args: List[str]) -> str:
        """处理 /list 命令"""
        if not self.client:
            return "[yellow]命令功能尚未完全实现，请稍候[/yellow]"
        
        try:
            limit = int(args[0]) if args else 10
            sessions = self.client.list_sessions(limit=limit)
            
            if not sessions:
                return "[dim]没有找到会话[/dim]"
            
            # 创建表格显示（优化样式）
            table = Table(
                title="[bold cyan]📋 最近会话[/bold cyan]",
                show_header=True,
                header_style="bold cyan",
                border_style="cyan",
                box=rich.box.ROUNDED
            )
            table.add_column("序号", style="cyan bold", width=6, justify="center")
            table.add_column("会话 ID", style="green", width=14)
            table.add_column("时间", style="yellow", width=18)
            table.add_column("预览", style="white", width=45)
            table.add_column("消息数", style="magenta bold", width=8, justify="center")
            
            for i, session in enumerate(sessions, 1):
                session_id = session.get("session_id", "N/A")
                updated_at = session.get("updated_at")
                if isinstance(updated_at, str):
                    from datetime import datetime
                    updated_at = datetime.fromisoformat(updated_at)
                time_str = updated_at.strftime("%Y-%m-%d %H:%M") if updated_at else "N/A"
                
                preview = session.get("preview", "")
                if len(preview) > 45:
                    preview = preview[:45] + "..."
                
                message_count = session.get("message_count", 0)
                
                table.add_row(
                    str(i),
                    session_id[:8] + "..." if len(session_id) > 8 else session_id,
                    time_str,
                    preview,
                    str(message_count)
                )
            
            # 使用 StringIO 捕获表格输出
            from io import StringIO
            output = StringIO()
            console = Console(file=output, width=120)
            console.print(table)
            return output.getvalue()
        except ValueError:
            return "[red]错误: limit 必须是数字[/red]"
        except Exception as e:
            return f"[red]错误: {e}[/red]"
    
    def _handle_search(self, args: List[str]) -> str:
        """处理 /search 命令 - 搜索包含关键词的会话"""
        if not args:
            return "[red]错误: /search 需要关键词参数[/red]\n用法: /search <keyword> [limit]"
        
        keyword = args[0]
        limit = int(args[1]) if len(args) > 1 else 10
        
        if not self.client:
            return "[yellow]命令功能尚未完全实现，请稍候[/yellow]"
        
        try:
            sessions = self.client.search_sessions(keyword, limit=limit)
            
            if not sessions:
                return f"[yellow]没有找到包含 '{keyword}' 的会话[/yellow]"
            
            # 创建表格显示（优化样式）
            table = Table(
                title=f"[bold yellow]🔍 搜索结果: '{keyword}'[/bold yellow]",
                show_header=True,
                header_style="bold yellow",
                border_style="yellow",
                box=rich.box.ROUNDED
            )
            table.add_column("序号", style="cyan bold", width=6, justify="center")
            table.add_column("会话 ID", style="green", width=14)
            table.add_column("时间", style="yellow", width=18)
            table.add_column("预览", style="white", width=45)
            table.add_column("消息数", style="magenta bold", width=8, justify="center")
            
            for i, session in enumerate(sessions, 1):
                session_id = session.get("session_id", "N/A")
                updated_at = session.get("updated_at")
                if isinstance(updated_at, str):
                    from datetime import datetime
                    updated_at = datetime.fromisoformat(updated_at)
                time_str = updated_at.strftime("%Y-%m-%d %H:%M") if updated_at else "N/A"
                
                preview = session.get("preview", "")
                if len(preview) > 45:
                    preview = preview[:45] + "..."
                
                message_count = session.get("message_count", 0)
                
                table.add_row(
                    str(i),
                    session_id[:8] + "..." if len(session_id) > 8 else session_id,
                    time_str,
                    preview,
                    str(message_count)
                )
            
            # 使用 StringIO 捕获表格输出
            from io import StringIO
            output = StringIO()
            console = Console(file=output, width=120)
            console.print(table)
            return output.getvalue()
        except ValueError:
            return "[red]错误: limit 必须是数字[/red]"
        except Exception as e:
            return f"[red]错误: {e}[/red]"
    
    def _handle_restore(self, args: List[str]) -> Tuple[str, Optional[str]]:
        """处理 /restore 命令 - 恢复会话（继续对话）
        
        支持两种方式：
        1. 使用序号：/restore 1 (从 /list 命令显示的序号)
        2. 使用会话 ID：/restore <session_id> (完整或部分 ID)
        
        Returns:
            (消息, 新的会话ID) - 如果恢复成功，返回新的会话ID
        """
        if not args:
            # 如果没有参数，恢复当前会话（如果存在）
            if self.current_session_id:
                return (f"[green]✓ 当前会话: {self.current_session_id[:8]}...[/green]", None)
            else:
                return ("[yellow]没有活动会话，请使用 /restore <序号|session_id> 恢复会话[/yellow]", None)
        
        identifier = args[0]
        
        if not self.client:
            return ("[yellow]命令功能尚未完全实现，请稍候[/yellow]", None)
        
        try:
            # 获取所有会话
            sessions = self.client.list_sessions(limit=1000)
            
            if not sessions:
                return ("[yellow]没有可用的会话[/yellow]", None)
            
            # 尝试作为序号处理（数字）
            try:
                index = int(identifier)
                if index < 1 or index > len(sessions):
                    return (f"[red]错误: 序号超出范围 (1-{len(sessions)})[/red]", None)
                # 序号从 1 开始，数组从 0 开始
                session = sessions[index - 1]
                session_id = session.get("session_id")
            except ValueError:
                # 不是数字，作为会话 ID 处理
                session_id = identifier
                session_ids = [s.get("session_id") for s in sessions]
                
                if session_id not in session_ids:
                    # 尝试匹配部分会话 ID
                    matching = [sid for sid in session_ids if sid.startswith(session_id)]
                    if len(matching) == 1:
                        session_id = matching[0]
                    elif len(matching) > 1:
                        return (f"[yellow]找到多个匹配的会话，请使用完整的会话 ID 或序号[/yellow]\n匹配的会话: {', '.join(matching[:5])}", None)
                    else:
                        return (f"[red]错误: 会话不存在: {session_id}[/red]\n提示: 可以使用序号恢复，例如 /restore 1", None)
            
            # 恢复成功
            return (f"[green]✓ 已恢复会话: {session_id[:8]}...[/green]\n[dim]可以继续对话了[/dim]", session_id)
        except Exception as e:
            return (f"[red]错误: {e}[/red]", None)
    
    def _handle_show(self, args: List[str]) -> str:
        """处理 /show 命令 - 显示会话详情（消息列表）
        
        支持三种方式：
        1. 无参数：/show (显示当前会话)
        2. 使用序号：/show 1 (从 /list 命令显示的序号)
        3. 使用会话 ID：/show <session_id> (完整或部分 ID)
        """
        if not self.client:
            return "[yellow]命令功能尚未完全实现，请稍候[/yellow]"
        
        # 如果没有参数，使用当前会话
        if not args:
            if not self.current_session_id:
                return "[yellow]当前没有活动会话，请先开始对话或切换会话[/yellow]"
            session_id = self.current_session_id
        else:
            identifier = args[0]
            
            try:
                # 获取所有会话
                sessions = self.client.list_sessions(limit=1000)
                
                if not sessions:
                    return "[yellow]没有可用的会话[/yellow]"
                
                # 尝试作为序号处理（数字）
                try:
                    index = int(identifier)
                    if index < 1 or index > len(sessions):
                        return f"[red]错误: 序号超出范围 (1-{len(sessions)})[/red]"
                    # 序号从 1 开始，数组从 0 开始
                    session = sessions[index - 1]
                    session_id = session.get("session_id")
                except ValueError:
                    # 不是数字，作为会话 ID 处理
                    session_id = identifier
                    session_ids = [s.get("session_id") for s in sessions]
                    
                    if session_id not in session_ids:
                        # 尝试匹配部分会话 ID
                        matching = [sid for sid in session_ids if sid.startswith(session_id)]
                        if len(matching) == 1:
                            session_id = matching[0]
                        elif len(matching) > 1:
                            return f"[yellow]找到多个匹配的会话，请使用完整的会话 ID 或序号[/yellow]\n匹配的会话: {', '.join(matching[:5])}"
                        else:
                            return f"[red]错误: 会话不存在: {session_id}[/red]\n提示: 可以使用序号查看，例如 /show 1"
            except Exception as e:
                return f"[red]错误: {e}[/red]"
        
        try:
            # 获取会话详情
            detail = self.client.get_session_detail(session_id)
            
            if not detail.get("success"):
                error_msg = detail.get('error', '获取失败')
                return f"[red]错误: {error_msg}[/red]"
            
            session_info = detail.get("session", {})
            messages = detail.get("messages", [])
            
            # 构建显示内容
            from datetime import datetime
            from rich.panel import Panel
            from rich.text import Text
            
            # 会话信息
            created_at = datetime.fromisoformat(session_info.get("created_at", ""))
            updated_at = datetime.fromisoformat(session_info.get("updated_at", ""))
            
            info_text = Text()
            info_text.append(f"会话 ID: {session_id}\n", style="cyan")
            info_text.append(f"创建时间: {created_at.strftime('%Y-%m-%d %H:%M:%S')}\n", style="dim")
            info_text.append(f"更新时间: {updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n", style="dim")
            info_text.append(f"消息数量: {len(messages)}\n", style="magenta")
            
            # 消息列表
            if messages:
                info_text.append("\n消息列表:\n", style="bold")
                for i, msg in enumerate(messages, 1):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    timestamp = datetime.fromisoformat(msg.get("timestamp", ""))
                    
                    role_color = "green" if role == "user" else "blue"
                    info_text.append(f"  [{i}] ", style="dim")
                    info_text.append(f"[{role}] ", style=role_color)
                    info_text.append(f"{timestamp.strftime('%H:%M:%S')} ", style="dim")
                    # 截断长内容
                    preview = content[:60] + "..." if len(content) > 60 else content
                    info_text.append(f"{preview}\n")
            else:
                info_text.append("\n[dim]暂无消息[/dim]\n")
            
            return Panel(
                info_text,
                border_style="cyan",
                title=f"[cyan]会话详情[/cyan]",
                padding=(1, 2)
            )
        except Exception as e:
            return f"[red]错误: {e}[/red]"
    
    def _handle_delete(self, args: List[str]) -> str:
        """处理 /delete 命令
        
        支持两种方式：
        1. 使用序号：/delete 1 (从 /list 命令显示的序号)
        2. 使用会话 ID：/delete <session_id> (完整或部分 ID)
        """
        if not args:
            return "[red]错误: /delete 需要会话 ID 或序号参数[/red]\n用法: /delete <序号|session_id>"
        
        identifier = args[0]
        
        if not self.client:
            return "[yellow]命令功能尚未完全实现，请稍候[/yellow]"
        
        try:
            # 获取所有会话
            sessions = self.client.list_sessions(limit=1000)
            
            if not sessions:
                return "[yellow]没有可用的会话[/yellow]"
            
            # 尝试作为序号处理（数字）
            try:
                index = int(identifier)
                if index < 1 or index > len(sessions):
                    return f"[red]错误: 序号超出范围 (1-{len(sessions)})[/red]"
                # 序号从 1 开始，数组从 0 开始
                session = sessions[index - 1]
                session_id = session.get("session_id")
            except ValueError:
                # 不是数字，作为会话 ID 处理
                session_id = identifier
                session_ids = [s.get("session_id") for s in sessions]
                
                if session_id not in session_ids:
                    # 尝试匹配部分会话 ID
                    matching = [sid for sid in session_ids if sid.startswith(session_id)]
                    if len(matching) == 1:
                        session_id = matching[0]
                    elif len(matching) > 1:
                        return f"[yellow]找到多个匹配的会话，请使用完整的会话 ID 或序号[/yellow]\n匹配的会话: {', '.join(matching[:5])}"
                    else:
                        return f"[red]错误: 会话不存在: {session_id}[/red]\n提示: 可以使用序号删除，例如 /delete 1"
            
            # 执行删除
            success = self.client.delete_session(session_id)
            
            if success:
                # 如果删除的是当前会话，提示用户
                if self.current_session_id == session_id:
                    return f"[green]✓ 会话已删除: {session_id[:8]}...[/green]\n[dim]提示: 当前会话已被删除，下次对话将创建新会话[/dim]"
                else:
                    return f"[green]✓ 会话已删除: {session_id[:8]}...[/green]"
            else:
                return f"[red]错误: 删除失败[/red]"
        except Exception as e:
            return f"[red]错误: {e}[/red]"
    
    def _handle_summary(self, args: List[str]) -> str:
        """处理 /summary 命令 - 生成并显示会话摘要
        
        支持两种方式：
        1. 使用序号：/summary 1 (从 /list 命令显示的序号)
        2. 使用会话 ID：/summary <session_id> (完整或部分 ID)
        """
        if not args:
            return "[red]错误: /summary 需要会话 ID 或序号参数[/red]\n用法: /summary <序号|session_id>"
        
        identifier = args[0]
        
        if not self.client:
            return "[yellow]命令功能尚未完全实现，请稍候[/yellow]"
        
        try:
            # 获取所有会话
            sessions = self.client.list_sessions(limit=1000)
            
            if not sessions:
                return "[yellow]没有可用的会话[/yellow]"
            
            # 尝试作为序号处理（数字）
            try:
                index = int(identifier)
                if index < 1 or index > len(sessions):
                    return f"[red]错误: 序号超出范围 (1-{len(sessions)})[/red]"
                # 序号从 1 开始，数组从 0 开始
                session = sessions[index - 1]
                session_id = session.get("session_id")
            except ValueError:
                # 不是数字，作为会话 ID 处理
                session_id = identifier
                session_ids = [s.get("session_id") for s in sessions]
                
                if session_id not in session_ids:
                    # 尝试匹配部分会话 ID
                    matching = [sid for sid in session_ids if sid.startswith(session_id)]
                    if len(matching) == 1:
                        session_id = matching[0]
                    elif len(matching) > 1:
                        return f"[yellow]找到多个匹配的会话，请使用完整的会话 ID 或序号[/yellow]\n匹配的会话: {', '.join(matching[:5])}"
                    else:
                        return f"[red]错误: 会话不存在: {session_id}[/red]\n提示: 可以使用序号生成摘要，例如 /summary 1"
            
            # 生成摘要
            from rich.panel import Panel
            from rich.text import Text
            
            result = self.client.generate_session_summary(session_id)
            
            if not result.get("success"):
                return f"[red]错误: {result.get('error', '生成失败')}[/red]"
            
            summary = result.get("summary", "")
            message_count = result.get("message_count", 0)
            
            summary_text = Text()
            summary_text.append(f"会话 ID: {session_id[:8]}...\n", style="cyan")
            summary_text.append(f"消息数量: {message_count}\n\n", style="magenta")
            summary_text.append("摘要:\n", style="bold")
            summary_text.append(summary, style="white")
            
            return Panel(
                summary_text,
                border_style="green",
                title="[green]会话摘要[/green]",
                padding=(1, 2)
            )
        except Exception as e:
            return f"[red]错误: {e}[/red]"
    
    def _handle_clear(self, args: List[str]) -> str:
        """处理 /clear 命令 - 清除当前会话的所有消息"""
        if not self.current_session_id:
            return "[yellow]当前没有活动会话[/yellow]"
        
        if not self.client:
            return "[yellow]命令功能尚未完全实现，请稍候[/yellow]"
        
        try:
            success = self.client.clear_session_messages(self.current_session_id)
            
            if success:
                return f"[green]✓ 当前会话的消息已清除[/green]\n[dim]会话 ID: {self.current_session_id[:8]}...[/dim]"
            else:
                return "[red]错误: 清除失败[/red]"
        except Exception as e:
            return f"[red]错误: {e}[/red]"
    
    def _handle_switch(self, args: List[str]) -> Tuple[str, Optional[str]]:
        """处理 /switch 命令
        
        支持两种方式：
        1. 使用序号：/switch 1 (从 /list 命令显示的序号)
        2. 使用会话 ID：/switch <session_id> (完整或部分 ID)
        
        Returns:
            (消息, 新的会话ID) - 如果切换成功，返回新的会话ID
        """
        if not args:
            return ("[red]错误: /switch 需要会话 ID 或序号参数[/red]\n用法: /switch <序号|session_id>", None)
        
        identifier = args[0]
        
        if not self.client:
            return ("[yellow]命令功能尚未完全实现，请稍候[/yellow]", None)
        
        try:
            # 获取所有会话
            sessions = self.client.list_sessions(limit=1000)
            
            if not sessions:
                return ("[yellow]没有可用的会话[/yellow]", None)
            
            # 尝试作为序号处理（数字）
            try:
                index = int(identifier)
                if index < 1 or index > len(sessions):
                    return (f"[red]错误: 序号超出范围 (1-{len(sessions)})[/red]", None)
                # 序号从 1 开始，数组从 0 开始
                session = sessions[index - 1]
                session_id = session.get("session_id")
                return (f"[green]✓ 已切换到会话 #{index}: {session_id[:8]}...[/green]", session_id)
            except ValueError:
                # 不是数字，作为会话 ID 处理
                pass
            
            # 作为会话 ID 处理
            session_id = identifier
            session_ids = [s.get("session_id") for s in sessions]
            
            if session_id not in session_ids:
                # 尝试匹配部分会话 ID
                matching = [sid for sid in session_ids if sid.startswith(session_id)]
                if len(matching) == 1:
                    session_id = matching[0]
                elif len(matching) > 1:
                    return (f"[yellow]找到多个匹配的会话，请使用完整的会话 ID 或序号[/yellow]\n匹配的会话: {', '.join(matching[:5])}", None)
                else:
                    return (f"[red]错误: 会话不存在: {session_id}[/red]\n提示: 可以使用序号切换，例如 /switch 1", None)
            
            # 切换成功
            return (f"[green]✓ 已切换到会话: {session_id[:8]}...[/green]", session_id)
        except Exception as e:
            return (f"[red]错误: {e}[/red]", None)
    
    def _handle_gvim(self, args: List[str]) -> str:
        """处理 /gvim 命令
        
        用法:
        /gvim <file_path> [line_number] [--read-only]
        /gvim --mediawiki <page_title> [line_number] [--read-only]
        """
        try:
            from backend.services.editor import GvimService, GvimServiceError
            
            if not args:
                return (
                    "[yellow]用法:[/yellow]\n"
                    "  /gvim <file_path> [line_number] [--read-only]\n"
                    "  /gvim --mediawiki <page_title> [line_number] [--read-only]\n"
                    "\n示例:\n"
                    "  /gvim /path/to/file.py 10\n"
                    "  /gvim --mediawiki Test\n"
                    "  /gvim --mediawiki Test 5 --read-only"
                )
            
            service = GvimService()
            
            if not service.check_availability():
                return "[red]错误: gvim 不可用，请确保已安装 gvim[/red]"
            
            # 解析参数
            file_path = None
            mediawiki_page = None
            line_number = None
            read_only = False
            
            i = 0
            while i < len(args):
                arg = args[i]
                if arg == '--mediawiki':
                    if i + 1 < len(args):
                        mediawiki_page = args[i + 1]
                        i += 2
                    else:
                        return "[red]错误: --mediawiki 需要指定页面标题[/red]"
                elif arg == '--read-only':
                    read_only = True
                    i += 1
                elif arg.isdigit():
                    line_number = int(arg)
                    i += 1
                else:
                    # 作为文件路径处理
                    if not file_path and not mediawiki_page:
                        file_path = arg
                    i += 1
            
            # 执行操作
            if mediawiki_page:
                result = service.open_mediawiki_page(
                    page_title=mediawiki_page,
                    line_number=line_number,
                    read_only=read_only
                )
                return f"[green]✓ {result['message']}[/green]\n文件路径: {result['file_path']}"
            elif file_path:
                result = service.open_file(
                    file_path=file_path,
                    line_number=line_number,
                    read_only=read_only
                )
                return f"[green]✓ {result['message']}[/green]"
            else:
                return "[red]错误: 必须指定文件路径或 MediaWiki 页面标题[/red]"
                
        except GvimServiceError as e:
            return f"[red]错误: {str(e)}[/red]"
        except Exception as e:
            return f"[red]错误: {str(e)}[/red]"
    
    def _handle_help(self, args: List[str]) -> str:
        """处理 /help 命令"""
        if args:
            command = args[0].lower()
            
            if command == 'context':
                return self._show_context_help()
            
            # 检查是否是上下文子命令
            if command in self.context_commands:
                desc, args_help = self.context_commands[command]
                return f"/context {command} {args_help}\n{desc}"
            
            # 检查是否是顶级命令
            if command in self.top_level_commands:
                desc, _ = self.top_level_commands[command]
                help_text = f"/{command}\n{desc}\n"
                
                # 如果是 context 命令，显示子命令
                if command == 'context':
                    help_text += "\n子命令:\n"
                    for sub_cmd, (sub_desc, sub_args) in self.context_commands.items():
                        sub_cmd_line = f"  /context {sub_cmd}"
                        if sub_args:
                            sub_cmd_line += f" {sub_args}"
                        sub_cmd_line += f" - {sub_desc}\n"
                        help_text += sub_cmd_line
                
                return help_text
            
            return f"未知命令: {command}\n输入 /help 查看帮助"
        else:
            return self._show_command_hint()

