"""表格组件"""
from rich.table import Table
from rich.console import Console

console = Console()

def create_table(title: str = None, **kwargs) -> Table:
    """创建表格"""
    table = Table(title=title, **kwargs)
    return table
















