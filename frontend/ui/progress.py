"""进度条组件"""
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.console import Console

console = Console()

def create_progress(description: str = "处理中...") -> Progress:
    """创建进度条"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    )













