"""CLI 主入口（前端主程序）"""
import click
from rich.console import Console
from frontend.client.ipc_client import IPCClient
from frontend.ui.panels import ChatPanel

console = Console()

@click.group()
def cli():
    """LLM Agent CLI Tool"""
    pass

@cli.command()
@click.argument('message', required=False)
def chat(message):
    """与 Agent 对话"""
    try:
        client = IPCClient()
    except ConnectionError as e:
        console.print(f"[bold red]错误: {e}[/bold red]")
        console.print("[yellow]提示: 请先启动后端服务 (python -m backend.main)[/yellow]")
        return
    
    if message:
        try:
            response = client.send(message)
            console.print(ChatPanel(response))
        except Exception as e:
            console.print(f"[bold red]错误: {e}[/bold red]")
    else:
        # 交互式模式
        console.print("[bold green]LLM Agent CLI[/bold green]")
        console.print("[yellow]输入 'exit' 或 'quit' 退出[/yellow]\n")
        
        while True:
            try:
                msg = console.input("[bold cyan]你: [/bold cyan]")
                if msg.lower() in ['exit', 'quit']:
                    break
                if not msg.strip():
                    continue
                
                response = client.send(msg)
                console.print(ChatPanel(response))
                console.print()  # 空行
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[bold red]错误: {e}[/bold red]")
    
    client.close()

if __name__ == '__main__':
    cli()

