"""面板组件"""
from rich.panel import Panel
from rich.markdown import Markdown
from rich.console import Console

console = Console()

def ChatPanel(message: str, role: str = "assistant") -> Panel:
    """创建聊天面板"""
    if role == "user":
        return Panel.fit(
            f"[bold cyan]{message}[/bold cyan]",
            border_style="cyan",
            title="[bold cyan]你[/bold cyan]"
        )
    else:
        return Panel(
            Markdown(message),
            border_style="green",
            title="[bold green]Agent[/bold green]"
        )

def ErrorPanel(error: str) -> Panel:
    """创建错误面板"""
    return Panel(
        f"[bold red]{error}[/bold red]",
        border_style="red",
        title="[bold red]错误[/bold red]"
    )

