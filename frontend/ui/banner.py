"""启动画面"""
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.box import DOUBLE, ROUNDED

console = Console()

def show_banner():
    """简洁的启动画面（参考 Cursor Agent）"""
    # 使用更醒目的显示方式，确保banner明显可见
    console.print()
    # 使用Panel包装，让banner更醒目
    banner_text = "[bold cyan]hou-cli[/bold cyan] - [bold]LLM Agent CLI[/bold]"
    console.print(Panel(
        banner_text,
        border_style="cyan",
        padding=(0, 2),
        box=ROUNDED
    ))
    console.print()

def show_banner_simple():
    """简洁版启动画面"""
    # 简洁的 ASCII 艺术字
    ascii_art = """
░█░█░█▀█░█░█░░░░░█▄█░█▀█░█▀█░█░█░█▀▀
░█▀█░█░█░█░█░▄▄▄░█░█░█▀█░█░█░█░█░▀▀█
░▀░▀░▀▀▀░▀▀▀░░░░░▀░▀░▀░▀░▀░▀░▀▀▀░▀▀▀
"""
    
    banner_text = Text(ascii_art.strip(), style="bold white")
    
    banner_panel = Panel(
        banner_text,
        border_style="white",
        box=ROUNDED,
        padding=(1, 2),
        title="[bold white]LLM Agent CLI[/bold white]",
        title_align="center"
    )
    
    console.print()
    console.print(banner_panel, justify="center")
    
    # 副标题
    subtitle = Text("hou-cli", style="dim italic")
    console.print(subtitle, justify="center")
    console.print()

def show_banner_minimal():
    """极简版启动画面"""
    ascii_art = """
╦ ╦╔═╗╔═╗     ╔═╗╦ ╦
╠═╣║╣ ║╣      ║ ║║║║
╩ ╩╚═╝╚═╝     ╚═╝╚╩╝
"""
    
    banner_text = Text(ascii_art.strip(), style="bold white")
    
    banner_panel = Panel(
        banner_text,
        border_style="white",
        padding=(1, 2),
        title="[bold white]LLM Agent CLI[/bold white]",
        title_align="center"
    )
    
    console.print()
    console.print(banner_panel, justify="center")
    
    # 副标题
    subtitle = Text("hou-cli", style="dim italic")
    console.print(subtitle, justify="center")
    console.print()
