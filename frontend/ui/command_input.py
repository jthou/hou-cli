"""交互式命令输入（支持命令提示和自动补全）"""
from typing import List, Optional, Callable
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False
    # 定义占位符以避免 NameError
    Completer = object
    Completion = object
    PromptSession = None
    KeyBindings = None
    Keys = None


class CommandCompleter(Completer):
    """命令自动补全器"""
    
    def __init__(self, commands: List[tuple]):
        """
        Args:
            commands: 命令列表，格式为 [(command, description, args), ...]
        """
        self.commands = commands
        self.command_names = [cmd[0] for cmd in commands]
    
    def get_completions(self, document, complete_event):
        """获取补全建议"""
        text = document.text_before_cursor
        
        # 只处理以 / 开头的命令
        if not text.startswith('/'):
            return
        
        # 提取当前输入的命令部分（去掉开头的 /）
        command_part = text[1:].strip()
        
        if not command_part:
            # 输入了 / 但还没有命令名，显示所有命令
            for cmd_name, desc, args in self.commands:
                display_text = f"/{cmd_name}"
                if args:
                    display_text += f" {args}"
                yield Completion(
                    f"/{cmd_name}",
                    start_position=-1,  # 替换 / 后面的空内容
                    display=display_text,
                    display_meta=desc
                )
        else:
            # 输入了部分命令名，补全命令名
            # 提取第一个词（命令名）
            parts = command_part.split()
            partial = parts[0].lower()
            
            for cmd_name, desc, args in self.commands:
                if cmd_name.startswith(partial):
                    # 计算需要替换的字符数
                    # 如果输入是 "/l"，text = "/l"，command_part = "l"，partial = "l"
                    # 光标在 "l" 后面，需要替换 "l"，所以 start_position = -1
                    # 补全文本应该是完整的命令（包括 /），这样 "/l" 会变成 "/list"
                    start_pos = -len(partial)
                    display_text = f"/{cmd_name}"
                    if args:
                        display_text += f" {args}"
                    yield Completion(
                        f"/{cmd_name}",
                        start_position=start_pos,
                        display=display_text,
                        display_meta=desc
                    )


class CommandInput:
    """交互式命令输入，支持命令提示和自动补全"""
    
    def __init__(self, console: Console, commands: List[tuple]):
        """
        Args:
            console: Rich Console 实例
            commands: 命令列表，格式为 [(command, description, args), ...]
        """
        self.console = console
        self.commands = commands
        
        if PROMPT_TOOLKIT_AVAILABLE:
            # 使用 prompt_toolkit 实现高级功能
            # 方法1: 使用 WordCompleter（更简单，但需要完整命令）
            from prompt_toolkit.completion import WordCompleter
            command_words = [f"/{cmd[0]}" for cmd in commands]
            # 使用 WordCompleter 作为基础，但我们需要自定义补全逻辑
            # 所以还是使用 CommandCompleter
            self.completer = CommandCompleter(commands)
            
            self.key_bindings = KeyBindings()
            self._setup_key_bindings()
            
            self.session = PromptSession(
                completer=self.completer,
                key_bindings=self.key_bindings,
                complete_style='multi-column',  # 多列显示补全建议
                complete_in_thread=False,  # 改为 False，确保补全立即响应
                enable_open_in_editor=False,  # 禁用编辑器模式
                enable_system_prompt=False,  # 禁用系统提示
            )
        else:
            self.completer = None
            self.key_bindings = None
            self.session = None
    
    def _setup_key_bindings(self):
        """设置快捷键绑定"""
        if PROMPT_TOOLKIT_AVAILABLE and self.key_bindings:
            @self.key_bindings.add(Keys.ControlSpace)
            def show_hint(event):
                """Ctrl+Space 显示命令提示"""
                self._show_command_hint()
    
    def _show_command_hint(self):
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
        
        self.console.print(Panel(
            hint_text,
            border_style="dim cyan",
            title="[dim cyan]命令提示[/dim cyan]",
            padding=(1, 2)
        ))
    
    def input(self, prompt: str = "[dim cyan]▸[/dim cyan] ") -> str:
        """
        带命令提示和自动补全的输入
        
        Args:
            prompt: 输入提示符
            
        Returns:
            用户输入的文本
        """
        if self.session:
            # 使用 prompt_toolkit
            try:
                text = self.session.prompt(prompt)
                
                # 如果输入的是单独的 '/'，显示命令提示
                if text.strip() == '/':
                    self._show_command_hint()
                    # 重新输入
                    text = self.session.prompt(prompt)
                
                return text
            except KeyboardInterrupt:
                raise
            except EOFError:
                return "exit"
        else:
            # 回退到简单的输入方式（使用 readline 如果可用）
            try:
                import readline
                
                # 设置命令补全
                def complete(text, state):
                    if not text.startswith('/'):
                        return None
                    # 提取命令部分
                    cmd_part = text[1:].strip().split()[0] if text[1:].strip() else ""
                    matches = []
                    for cmd_name, _, _ in self.commands:
                        if cmd_name.startswith(cmd_part.lower()):
                            matches.append(f"/{cmd_name}")
                    if state < len(matches):
                        return matches[state]
                    return None
                
                readline.set_completer(complete)
                readline.parse_and_bind("tab: complete")
                
                text = self.console.input(prompt)
                
                # 如果输入的是单独的 '/'，显示命令提示
                if text.strip() == '/':
                    self._show_command_hint()
                    # 重新输入
                    text = self.console.input(prompt)
                
                return text
            except ImportError:
                # 没有 readline（Windows），使用最简版本
                text = self.console.input(prompt)
                
                # 如果输入的是单独的 '/'，显示命令提示
                if text.strip() == '/':
                    self._show_command_hint()
                    # 重新输入
                    text = self.console.input(prompt)
                
                return text
    
    def input_simple(self, prompt: str = "[dim cyan]▸[/dim cyan] ") -> str:
        """
        简化版本的命令提示输入（不使用 prompt_toolkit）
        
        Args:
            prompt: 输入提示符
            
        Returns:
            用户输入的文本
        """
        return self.console.input(prompt)

