"""CLI 主入口（前端主程序）"""
import os
import asyncio
import uuid
from pathlib import Path
from dotenv import load_dotenv
import click
from rich.console import Console
from frontend.client.ipc_client import IPCClient
# 移除 ChatPanel 导入，直接使用 RendererFactory
from frontend.ui.banner import show_banner
from frontend.ui.renderer import RendererFactory
from frontend.ui.stream_handler import StreamRenderer
from frontend.ui.command_handler import CommandHandler

# 加载 .env 文件
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

console = Console()

def show_error(error: Exception, context: str = ""):
    """显示友好的错误提示"""
    from rich.panel import Panel
    
    error_msg = str(error)
    suggestion = ""
    
    # 根据错误类型提供建议
    if "ConnectionError" in str(type(error)) or "连接" in error_msg:
        suggestion = "提示: 请检查后端服务是否正常运行"
    elif "DEEPSEEK_API_KEY" in error_msg:
        suggestion = "提示: 请检查 .env 文件中的 DEEPSEEK_API_KEY 配置"
    else:
        suggestion = "提示: 请查看错误信息并重试"
    
    console.print(Panel(
        f"[bold red]✗ 错误[/bold red]: {error_msg}\n"
        f"[dim]{suggestion}[/dim]",
        border_style="red",
        title="[bold red]错误[/bold red]"
    ))

@click.group()
def cli():
    """LLM Agent CLI Tool"""
    pass

async def _stream_chat(client: IPCClient, message: str, session_id: str = None):
    """流式聊天（异步）"""
    # 移除 Agent 前缀，直接显示内容
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
        console.print(f"\n[bold red]✗ 错误[/bold red]: {e}")
        return None

@cli.command()
@click.argument('message', required=False)
@click.option('--stream/--no-stream', default=True, help='是否使用流式响应')
def chat(message, stream):
    """与 Agent 对话"""
    try:
        client = IPCClient()
    except ConnectionError as e:
        show_error(e)
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
                # 直接渲染内容，不使用 Panel
                factory = RendererFactory()
                renderer = factory.get_renderer(response)
                rendered = renderer.render(response)
                console.print(rendered)
                console.print()  # 空行分隔
        except Exception as e:
            show_error(e)
    else:
        # 交互式模式
        # 显示启动画面
        show_banner()
        console.print("[dim]输入 'exit' 或 'quit' 退出[/dim]\n")
        # 会话 ID 在后台使用，不显示给用户
        
        # 创建命令处理器
        command_handler = CommandHandler(client=client, current_session_id=session_id)
        
        while True:
            try:
                msg = console.input("[dim cyan]▸[/dim cyan] ")
                if msg.lower() in ['exit', 'quit']:
                    break
                if not msg.strip():
                    continue
                
                # 检测命令模式（以 / 开头）
                if msg.startswith('/'):
                    result, new_session_id = command_handler.handle_command(msg)
                    if result:
                        console.print(result)
                    # 如果命令返回了新的会话 ID，更新当前会话
                    if new_session_id:
                        session_id = new_session_id
                        command_handler.current_session_id = session_id
                        console.print(f"[dim]当前会话: {session_id[:8]}...[/dim]")
                    console.print()  # 空行
                    continue
                
                # 正常对话流程
                if stream:
                    # 流式响应
                    asyncio.run(_stream_chat(client, msg, session_id=session_id))
                else:
                    # 非流式响应
                    response = client.send(msg, session_id=session_id)
                    # 直接渲染内容，不使用 Panel
                    factory = RendererFactory()
                    renderer = factory.get_renderer(response)
                    rendered = renderer.render(response)
                    console.print(rendered)
                console.print()  # 空行
            except KeyboardInterrupt:
                break
            except Exception as e:
                show_error(e)
    
    client.close()

if __name__ == '__main__':
    cli()

