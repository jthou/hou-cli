"""启动画面"""
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.box import DOUBLE, ROUNDED

console = Console()

def show_banner():
    """显示启动画面 - 增强版"""
    # ASCII 艺术字 - HOU (使用标准 ASCII 字符，更清晰)
    ascii_art = r"""
░█░█░█▀▀░█░░░█░░░█▀█░░░░░█░█░█▀█░█░█░░░░░█▀▀░█░░░▀█▀
░█▀█░█▀▀░█░░░█░░░█░█░░░░░█▀█░█░█░█░█░▄▄▄░█░░░█░░░░█░
░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▄▀░░▀░▀░▀▀▀░▀▀▀░░░░░▀▀▀░▀▀▀░▀▀▀
"""
    
    # 创建黑白文本
    banner_text = Text()
    lines = ascii_art.strip().split('\n')
    
    # 为每一行添加黑白样式
    for i, line in enumerate(lines):
        if line.strip():
            banner_text.append(line, style="white")
            if i < len(lines) - 1:
                banner_text.append("\n")
    
    # 创建装饰性面板
    banner_panel = Panel(
        banner_text,
        border_style="white",
        box=DOUBLE,
        padding=(1, 3),
        title="[bold white]╔═══ LLM Agent CLI ═══╗[/bold white]",
        title_align="center"
    )
    
    console.print()
    console.print(banner_panel, justify="center")
    
    # 显示副标题，带装饰
    subtitle = Text()
    subtitle.append("─" * 15, style="dim")
    subtitle.append(" hou-cli ", style="italic white")
    subtitle.append("─" * 15, style="dim")
    console.print(subtitle, justify="center")
    console.print()  # 空行

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
