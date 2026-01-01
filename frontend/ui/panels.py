"""面板组件"""
from rich.panel import Panel
from rich.console import Console
from frontend.ui.renderer import RendererFactory

console = Console()

# 创建全局工厂实例
_renderer_factory = RendererFactory()


def ChatPanel(message: str, role: str = "assistant") -> Panel:
    """创建聊天面板"""
    if role == "user":
        return Panel.fit(
            f"[bold cyan]{message}[/bold cyan]",
            border_style="cyan",
            title="[bold cyan]你[/bold cyan]"
        )
    else:
        # 使用渲染器工厂渲染内容
        renderer = _renderer_factory.get_renderer(message)
        rendered = renderer.render(message)
        
        return Panel(
            rendered,
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

