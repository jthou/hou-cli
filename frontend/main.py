"""CLI 主入口（前端主程序）"""
import os
import asyncio
import uuid
from pathlib import Path
from dotenv import load_dotenv
import click
from rich.console import Console
from frontend.client.ipc_client import IPCClient
from frontend.ui.panels import ChatPanel
from frontend.ui.banner import show_banner
from frontend.ui.renderer import RendererFactory
from frontend.ui.stream_handler import StreamRenderer

# 加载 .env 文件
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

console = Console()

@click.group()
def cli():
    """LLM Agent CLI Tool"""
    pass

async def _stream_chat(client: IPCClient, message: str, session_id: str = None):
    """流式聊天（异步）"""
    console.print("[bold cyan]Agent: [/bold cyan]", end="")
    
    try:
        # 创建渲染器
        factory = RendererFactory()
        stream_renderer = StreamRenderer(factory)
        
        # 创建流式数据生成器
        async def stream_generator():
            async for chunk in client.stream_send(message, session_id=session_id):
                yield chunk
        
        # 使用 StreamRenderer 实时渲染
        await stream_renderer.render_stream(stream_generator(), console)
        console.print()  # 换行
        
        return True
    except Exception as e:
        console.print(f"\n[bold red]错误: {e}[/bold red]")
        return None

@cli.command()
@click.argument('message', required=False)
@click.option('--stream/--no-stream', default=True, help='是否使用流式响应')
def chat(message, stream):
    """与 Agent 对话"""
    try:
        client = IPCClient()
    except ConnectionError as e:
        console.print(f"[bold red]错误: {e}[/bold red]")
        console.print("[yellow]提示: 请先启动后端服务 (python -m backend.main)[/yellow]")
        return
    
    # 创建会话 ID（用于维护对话上下文）
    session_id = str(uuid.uuid4())
    
    if message:
        # 单次对话
        try:
            if stream:
                # 流式响应
                asyncio.run(_stream_chat(client, message, session_id=session_id))
            else:
                # 非流式响应
                response = client.send(message, session_id=session_id)
                console.print(ChatPanel(response))
        except Exception as e:
            console.print(f"[bold red]错误: {e}[/bold red]")
    else:
        # 交互式模式
        # 显示启动画面
        show_banner()
        console.print("[yellow]输入 'exit' 或 'quit' 退出[/yellow]")
        console.print(f"[dim]会话 ID: {session_id}[/dim]\n")
        
        while True:
            try:
                msg = console.input("[bold cyan]你: [/bold cyan]")
                if msg.lower() in ['exit', 'quit']:
                    break
                if not msg.strip():
                    continue
                
                if stream:
                    # 流式响应
                    asyncio.run(_stream_chat(client, msg, session_id=session_id))
                else:
                    # 非流式响应
                    response = client.send(msg, session_id=session_id)
                    console.print(ChatPanel(response))
                console.print()  # 空行
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[bold red]错误: {e}[/bold red]")
    
    client.close()

if __name__ == '__main__':
    cli()

