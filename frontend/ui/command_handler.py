"""命令处理器（类似 Cursor Agent 的命令模式）"""
from typing import List, Dict, Any, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


class CommandHandler:
    """命令处理器"""
    
    def __init__(self, client=None, current_session_id: Optional[str] = None):
        self.client = client
        self.current_session_id = current_session_id
        self.console = Console()
        self.commands = [
            ("list", "列出最近的会话", "[limit]"),
            ("search", "搜索包含关键词的会话", "<keyword> [limit]"),
            ("restore", "恢复会话（继续对话）", "[session_id]"),
            ("show", "显示会话详情", "<session_id>"),
            ("delete", "删除指定会话", "<session_id>"),
            ("summary", "生成并显示会话摘要", "<session_id>"),
            ("clear", "清除当前会话的所有消息", ""),
            ("switch", "切换到指定会话", "<session_id>"),
            ("help", "显示帮助信息", "[command]"),
        ]
    
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
        
        # 路由到对应的命令处理函数
        handlers = {
            'list': self._handle_list,
            'search': self._handle_search,
            'restore': self._handle_restore,
            'show': self._handle_show,
            'delete': self._handle_delete,
            'summary': self._handle_summary,
            'clear': self._handle_clear,
            'switch': self._handle_switch,
            'help': self._handle_help,
        }
        
        handler = handlers.get(command)
        if handler:
            try:
                result = handler(args)
                # 如果返回的是元组 (message, session_id)，直接返回
                if isinstance(result, tuple) and len(result) == 2:
                    return result
                # 否则返回 (message, None)
                return (result, None)
            except Exception as e:
                return (f"[red]错误: {e}[/red]", None)
        else:
            return (f"[yellow]未知命令: {command}[/yellow]\n输入 /help 查看帮助", None)
    
    def _show_command_hint(self) -> str:
        """显示命令提示菜单"""
        hint_text = Text()
        hint_text.append("可用命令:\n", style="dim")
        
        for cmd, desc, args in self.commands:
            cmd_line = f"  [cyan]/{cmd}[/cyan]"
            if args:
                cmd_line += f" {args}"
            cmd_line += f" - {desc}\n"
            hint_text.append(cmd_line)
        
        hint_text.append("\n[dim]提示: 输入命令后按 Enter 执行，按 Tab 自动补全[/dim]")
        
        return Panel(
            hint_text,
            border_style="dim cyan",
            title="[dim cyan]命令提示[/dim cyan]",
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
            
            # 创建表格显示
            table = Table(title="最近会话")
            table.add_column("序号", style="cyan", width=6)
            table.add_column("会话 ID", style="green", width=12)
            table.add_column("时间", style="yellow", width=16)
            table.add_column("预览", style="white", width=50)
            table.add_column("消息数", style="magenta", width=8)
            
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
        """处理 /search 命令"""
        if not args:
            return "[red]错误: /search 需要关键词参数[/red]\n用法: /search <keyword> [limit]"
        return "[yellow]命令功能正在开发中，敬请期待[/yellow]"
    
    def _handle_restore(self, args: List[str]) -> str:
        """处理 /restore 命令"""
        return "[yellow]命令功能正在开发中，敬请期待[/yellow]"
    
    def _handle_show(self, args: List[str]) -> str:
        """处理 /show 命令"""
        if not args:
            return "[red]错误: /show 需要会话 ID 参数[/red]\n用法: /show <session_id>"
        return "[yellow]命令功能正在开发中，敬请期待[/yellow]"
    
    def _handle_delete(self, args: List[str]) -> str:
        """处理 /delete 命令"""
        if not args:
            return "[red]错误: /delete 需要会话 ID 参数[/red]\n用法: /delete <session_id>"
        return "[yellow]命令功能正在开发中，敬请期待[/yellow]"
    
    def _handle_summary(self, args: List[str]) -> str:
        """处理 /summary 命令"""
        if not args:
            return "[red]错误: /summary 需要会话 ID 参数[/red]\n用法: /summary <session_id>"
        return "[yellow]命令功能正在开发中，敬请期待[/yellow]"
    
    def _handle_clear(self, args: List[str]) -> str:
        """处理 /clear 命令"""
        return "[yellow]命令功能正在开发中，敬请期待[/yellow]"
    
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
    
    def _handle_help(self, args: List[str]) -> str:
        """处理 /help 命令"""
        if args:
            command = args[0].lower()
            help_texts = {
                'list': '/list [limit] - 列出最近的会话',
                'search': '/search <keyword> [limit] - 搜索包含关键词的会话',
                'restore': '/restore [session_id] - 恢复会话（继续对话）',
                'show': '/show <session_id> - 显示会话详情',
                'delete': '/delete <session_id> - 删除指定会话',
                'summary': '/summary <session_id> - 生成并显示会话摘要',
                'clear': '/clear - 清除当前会话的所有消息',
                'switch': '/switch <session_id> - 切换到指定会话',
                'help': '/help [command] - 显示帮助信息',
            }
            return help_texts.get(command, f"未知命令: {command}")
        else:
            return self._show_command_hint()

