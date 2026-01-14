"""CLI 主入口（前端主程序）"""
import os
import sys
import asyncio
import uuid
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import click
from rich.console import Console
from frontend.client.ipc_client import IPCClient
# 移除 ChatPanel 导入，直接使用 RendererFactory
from frontend.ui.banner import show_banner
from frontend.ui.renderer import RendererFactory
from frontend.ui.stream_handler import StreamRenderer
from frontend.ui.command_handler import CommandHandler

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 加载 .env 文件
# 优先级：1. 用户配置目录 2. 项目根目录 3. 当前目录
# 注意：在打包后的环境中，不应该有项目根目录的 .env
from shared.platform_utils import get_app_data_dir

# 检测是否是打包后的环境
# 方法1: 检查模块路径
_is_packaged = False
try:
    _module_path = Path(__file__).absolute()
    _is_packaged = '/opt/hou-cli' in str(_module_path) or '/usr/local/bin' in str(_module_path) or '/usr/share' in str(_module_path)
except:
    pass

# 方法2: 检查 Python 可执行文件路径（更可靠）
if not _is_packaged:
    try:
        import sys
        _python_exe = Path(sys.executable).absolute()
        _is_packaged = '/opt/hou-cli/venv' in str(_python_exe)
    except:
        pass

config_dir = Path.home() / ".config" / "hou-cli"
env_paths = [
    config_dir / ".env",  # 用户配置目录（推荐，打包后环境）
]

# 如果不是打包后的环境，添加项目根目录和当前目录（开发环境）
if not _is_packaged:
    env_paths.extend([
        Path(__file__).parent.parent / '.env',  # 项目根目录（开发环境）
        Path.cwd() / '.env',  # 当前目录
    ])

env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        env_loaded = True
        break

if not env_loaded:
    # 如果都没找到，尝试从当前目录加载（兼容旧行为）
    load_dotenv()

console = Console()

def _get_session_file() -> Path:
    """获取会话文件路径（跨平台）"""
    import platform
    if platform.system() == "Windows":
        base = Path.home() / "AppData" / "Local" / "hou-cli"
    elif platform.system() == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support" / "hou-cli"
    else:  # Linux
        base = Path.home() / ".local" / "share" / "hou-cli"
    
    base.mkdir(parents=True, exist_ok=True)
    return base / "last_session.txt"

def save_session_id(session_id: str):
    """保存会话 ID 到文件"""
    try:
        session_file = _get_session_file()
        session_file.write_text(session_id.strip())
    except Exception:
        # 保存失败不影响主流程，静默处理
        pass

def load_session_id() -> Optional[str]:
    """从文件加载会话 ID"""
    try:
        session_file = _get_session_file()
        if session_file.exists():
            session_id = session_file.read_text().strip()
            if session_id:
                return session_id
    except Exception:
        # 加载失败返回 None，将创建新会话
        pass
    return None

def show_error(error: Exception, context: str = ""):
    """显示友好的错误提示"""
    from rich.panel import Panel
    
    # #region agent log
    try:
        import json
        debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
        debug_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(debug_log_path, 'a', encoding='utf-8') as f:
            json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:show_error","message":"显示错误","data":{"error_type":type(error).__name__},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
            f.write('\n')
    except: pass
    # #endregion
    # 安全地获取错误消息
    try:
        error_msg = str(error)
    except UnicodeDecodeError as e:
        # #region agent log
        try:
            import json
            debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
            debug_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:show_error","message":"str(error)失败","data":{"error_type":type(e).__name__,"error_msg":repr(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                f.write('\n')
        except: pass
        # #endregion
        # 如果 str(error) 失败，使用 repr 或默认消息
        try:
            error_msg = repr(error)
        except:
            error_msg = f"{type(error).__name__}: 编码错误，无法显示详细信息"
    except Exception as e:
        # #region agent log
        try:
            import json
            debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
            debug_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:show_error","message":"str(error)异常","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                f.write('\n')
        except: pass
        # #endregion
        error_msg = f"{type(error).__name__}: 无法获取错误消息"
    # 清理无效的 Unicode 字符
    try:
        error_msg = error_msg.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
    except Exception as e:
        # #region agent log
        try:
            import json
            debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
            debug_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:show_error","message":"错误消息编码失败","data":{"error":str(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                f.write('\n')
        except: pass
        # #endregion
        error_msg = error_msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    
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
    import json
    import time
    # #region agent log
    try:
        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frontend/main.py:_stream_chat:entry","message":"_stream_chat函数被调用","data":{"message_length":len(message) if message else 0,"session_id":session_id},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
            f.flush()
    except: pass
    # #endregion
    
    # 移除 Agent 前缀，直接显示内容
    try:
        # 创建渲染器
        factory = RendererFactory()
        stream_renderer = StreamRenderer(factory)
        
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frontend/main.py:_stream_chat:before_stream_send","message":"准备调用stream_send","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        # 创建流式数据生成器
        async def stream_generator():
            try:
                # #region agent log
                try:
                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frontend/main.py:stream_generator:before_async_for","message":"准备进入stream_send循环","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                        f.flush()
                except: pass
                # #endregion
                
                chunk_count = 0
                async for chunk in client.stream_send(message, session_id=session_id):
                    chunk_count += 1
                    # #region agent log
                    if chunk_count <= 3:  # 只记录前3个chunk
                        try:
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frontend/main.py:stream_generator:received_chunk","message":"收到chunk","data":{"chunk_count":chunk_count,"chunk_preview":chunk[:50] if chunk else None},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                    # #endregion
                    # 清理无效的 Unicode 字符
                    try:
                        chunk = chunk.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
                    except Exception:
                        chunk = chunk.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                    yield chunk
            except KeyboardInterrupt:
                # 用户按 Ctrl+C，终止流式请求
                yield "\n\n[bold yellow]⚠ 用户中断[/bold yellow]: 对话已终止\n"
                raise  # 重新抛出，让外层处理
            except ConnectionError as e:
                # 连接错误，显示友好提示
                try:
                    error_msg = str(e)
                except (UnicodeDecodeError, UnicodeEncodeError):
                    error_msg = "流式请求连接错误：编码错误"
                except Exception:
                    error_msg = "流式请求连接错误：无法获取错误消息"
                if not error_msg:
                    error_msg = "流式请求连接错误：连接已断开"
                yield f"\n\n[bold red]✗ 连接错误[/bold red]: {error_msg}\n"
                # 如果错误信息中已经包含提示，就不再重复显示
                if "提示:" not in error_msg:
                    yield "[dim]提示: 请检查后端服务是否正常运行，或任务是否过于复杂导致超时[/dim]\n"
            except Exception as e:
                # 其他错误
                try:
                    error_msg = str(e)
                except (UnicodeDecodeError, UnicodeEncodeError):
                    error_msg = f"{type(e).__name__}: 编码错误"
                except Exception:
                    error_msg = f"{type(e).__name__}: 无法获取错误消息"
                yield f"\n\n[bold red]✗ 错误[/bold red]: {error_msg}\n"
        
        # 使用 StreamRenderer 实时渲染
        try:
            await stream_renderer.render_stream(stream_generator(), console)
            console.print()  # 换行
        except KeyboardInterrupt:
            # 用户按 Ctrl+C，显示提示并终止
            console.print("\n[bold yellow]⚠ 对话已终止[/bold yellow]")
            console.print("[dim]提示: 按 Ctrl+C 可以随时终止正在进行的对话[/dim]\n")
            return False
        except UnicodeDecodeError as e:
            # #region agent log
            try:
                import json
                debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
                debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(debug_log_path, 'a', encoding='utf-8') as f:
                    json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:_stream_chat","message":"UnicodeDecodeError in render_stream","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200],"start":getattr(e,'start',None),"end":getattr(e,'end',None)},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                    f.write('\n')
            except: pass
            # #endregion
            # Unicode 解码错误，使用安全的错误处理
            try:
                error_msg = f"编码错误: 位置 {getattr(e, 'start', '?')}-{getattr(e, 'end', '?')}"
            except:
                error_msg = "编码错误: 无法解码数据"
            show_error(e)
            return False
        except Exception as e:
            # #region agent log
            try:
                import json
                debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
                debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(debug_log_path, 'a', encoding='utf-8') as f:
                    json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:_stream_chat","message":"Exception in render_stream","data":{"error_type":type(e).__name__,"error_msg":str(e)[:500],"error_repr":repr(e)[:500]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                    f.write('\n')
            except: pass
            # #endregion
            # 确保异常对象不是 Panel，如果是则提取错误信息
            if isinstance(e, Exception):
                show_error(e)
            else:
                # 如果不是异常对象，直接显示
                try:
                    error_msg = str(e)
                except:
                    error_msg = repr(e)
                show_error(Exception(error_msg))
            return False
        
        return True
    except UnicodeDecodeError as e:
        # #region agent log
        try:
            import json
            debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
            debug_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:_stream_chat","message":"UnicodeDecodeError in outer try","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                f.write('\n')
        except: pass
        # #endregion
        # 如果是 Panel 对象异常，转换为普通异常
        if hasattr(e, '__class__') and 'Panel' in str(type(e)):
            e = Exception(f"Panel对象异常: {str(e)}")
        show_error(e)
        return None
    except Exception as e:
        # #region agent log
        try:
            import json
            debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
            debug_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:_stream_chat","message":"Exception in outer try","data":{"error_type":type(e).__name__,"error_msg":str(e)[:500],"error_repr":repr(e)[:500],"is_panel":hasattr(e,'__class__') and 'Panel' in str(type(e))},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                f.write('\n')
        except: pass
        # #endregion
        # 如果是 Panel 对象异常，转换为普通异常
        if hasattr(e, '__class__') and 'Panel' in str(type(e)):
            e = Exception(f"Panel对象异常: {str(e)}")
        show_error(e)
        return None

def check_config():
    """检查配置是否已设置"""
    # 重新加载配置（确保使用最新的配置）
    # 优先检查用户配置目录（打包后的环境）
    config_dir = Path.home() / ".config" / "hou-cli"
    user_env = config_dir / ".env"
    
    # 清除之前加载的环境变量（避免项目根目录的 .env 干扰）
    if 'DEEPSEEK_API_KEY' in os.environ:
        del os.environ['DEEPSEEK_API_KEY']
    
    # 如果用户配置文件存在，重新加载
    if user_env.exists():
        load_dotenv(user_env, override=True)
    else:
        # 如果没有用户配置，检查项目根目录（仅开发环境）
        # 检测是否是打包后的环境
        is_packaged = False
        try:
            # 方法1: 检查模块路径
            _module_path = Path(__file__).absolute()
            is_packaged = '/opt/hou-cli' in str(_module_path) or '/usr/local/bin' in str(_module_path) or '/usr/share' in str(_module_path)
        except:
            pass
        
        # 方法2: 检查 Python 可执行文件路径（更可靠）
        if not is_packaged:
            try:
                import sys
                _python_exe = Path(sys.executable).absolute()
                is_packaged = '/opt/hou-cli/venv' in str(_python_exe)
            except:
                pass
        
        # 只在开发环境中使用项目根目录的 .env
        if not is_packaged:
            project_env = Path(__file__).parent.parent / '.env'
            if project_env.exists():
                load_dotenv(project_env, override=True)
    
    # 检查 API Key
    api_key = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if not api_key or len(api_key) < 10:
        from rich.panel import Panel
        console.print(Panel(
            "[bold yellow]⚠️  配置未完成[/bold yellow]\n\n"
            "请先配置 API 密钥才能使用。\n\n"
            "[bold]配置步骤：[/bold]\n"
            "1. 编辑配置文件: [cyan]~/.config/hou-cli/.env[/cyan]\n"
            "2. 填入你的 DEEPSEEK_API_KEY\n"
            "3. 保存后重新运行\n\n"
            "[dim]配置示例位置: /usr/share/hou-cli/env.example[/dim]\n"
            "[dim]快速配置: cp /usr/share/hou-cli/env.example ~/.config/hou-cli/.env[/dim]",
            border_style="yellow",
            title="[bold yellow]配置提示[/bold yellow]"
        ))
        return False
    return True

@cli.command()
@click.argument('message', required=False)
@click.option('--stream/--no-stream', default=True, help='是否使用流式响应')
def chat(message, stream):
    """与 Agent 对话"""
    # 检查配置（在显示 banner 之前）
    if not check_config():
        sys.exit(1)
    
    # 如果是交互式模式，先显示 banner（在连接之前显示，确保总是显示）
    banner_shown = False
    if not message:
        show_banner()
        console.print("[dim]输入 'exit' 或 'quit' 退出，按 Ctrl+C 可终止正在进行的对话[/dim]\n")
        banner_shown = True
    
    try:
        client = IPCClient()
    except ConnectionError as e:
        # 连接失败时，确保banner已显示（交互式模式）
        if not banner_shown and not message:
            show_banner()
            console.print("[dim]输入 'exit' 或 'quit' 退出，按 Ctrl+C 可终止正在进行的对话[/dim]\n")
        # 显示错误信息（不会覆盖banner，因为banner在上面）
        show_error(e)
        return
    
    # 尝试加载上次的会话 ID（仅在交互式模式下）
    session_id = None
    if not message:  # 交互式模式才恢复会话
        session_id = load_session_id()
        
        if session_id:
            # 直接使用上次的会话 ID，不验证是否存在
            # 如果会话不存在，后端会在第一次发送消息时自动创建
            console.print(f"[dim]已恢复上次会话: {session_id[:8]}...[/dim]")
        else:
            # 如果没有保存的会话，创建新会话
            session_id = str(uuid.uuid4())
            console.print(f"[dim]已创建新会话: {session_id[:8]}...[/dim]")
            # 注意：会话 ID 会在第一次成功发送消息后保存
    else:
        # 单次对话模式，创建新会话
        session_id = str(uuid.uuid4())
    
    if message:
        # 单次对话
        try:
            if stream:
                # 流式响应
                try:
                    asyncio.run(_stream_chat(client, message, session_id=session_id))
                except KeyboardInterrupt:
                    # 用户按 Ctrl+C，显示提示
                    console.print("\n[bold yellow]⚠ 对话已终止[/bold yellow]\n")
                    return
            else:
                # 非流式响应
                response = client.send(message, session_id=session_id)
                # 直接渲染内容，不使用 Panel
                factory = RendererFactory()
                renderer = factory.get_renderer(response)
                rendered = renderer.render(response)
                
                # 检查是否为列表（某些渲染器可能返回列表）
                if isinstance(rendered, list):
                    for item in rendered:
                        console.print(item)
                else:
                    console.print(rendered)
                console.print()  # 空行分隔
        except Exception as e:
            show_error(e)
    else:
        # 交互式模式
        # Banner 已经在上面显示了
        # 会话 ID 在后台使用，不显示给用户
        
        # 创建命令处理器
        command_handler = CommandHandler(client=client, current_session_id=session_id)
        
        # 设置命令历史（使用 readline）
        try:
            import readline
            # 设置历史文件路径
            import os
            from pathlib import Path
            
            # 创建历史文件目录
            if sys.platform == "Windows":
                history_dir = Path.home() / "AppData" / "Local" / "hou-cli"
            elif sys.platform == "Darwin":  # macOS
                history_dir = Path.home() / "Library" / "Application Support" / "hou-cli"
            else:  # Linux
                history_dir = Path.home() / ".local" / "share" / "hou-cli"
            
            history_dir.mkdir(parents=True, exist_ok=True)
            history_file = history_dir / "history.txt"
            
            # 加载历史记录
            try:
                readline.read_history_file(str(history_file))
            except FileNotFoundError:
                pass
            
            # 设置历史记录长度
            readline.set_history_length(1000)
        except ImportError:
            # readline 不可用（Windows），跳过
            readline = None
            history_file = None
        
        while True:
            try:
                msg = console.input("[dim cyan]▸[/dim cyan] ")
                
                # 保存到历史记录
                if readline and msg.strip():
                    readline.add_history(msg.strip())
                if msg.lower() in ['exit', 'quit']:
                    break
                if not msg.strip():
                    continue
                
                # 检测命令模式（以 / 开头）
                if msg.startswith('/'):
                    # 检查是否是退出命令
                    if msg.strip().lower() in ['/exit', '/quit']:
                        break
                    
                    result, new_session_id = command_handler.handle_command(msg)
                    # #region agent log
                    try:
                        import json
                        import time
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:chat:after_handle_command","message":"handle_command返回","data":{"result_type":type(result).__name__ if result else None,"result_type_str":str(type(result)) if result else None,"is_panel":hasattr(result,'__class__') and 'Panel' in str(type(result)) if result else False,"is_str":isinstance(result, str) if result else False},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                            f.flush()
                    except: pass
                    # #endregion
                    if result:
                        # result 可能是字符串或 Rich 对象（如 Panel）
                        # #region agent log
                        try:
                            import json
                            import time
                            result_type_name = type(result).__name__
                            result_type_str = str(type(result))
                            is_panel_check = hasattr(result, '__class__') and 'Panel' in str(type(result))
                            # 避免将 Panel 对象转换为字符串，直接检查类型
                            if hasattr(result, '__class__') and 'Panel' in str(type(result)):
                                result_preview = f"<Panel object at {id(result)}>"
                            else:
                                result_preview = str(result)[:100] if hasattr(result, '__str__') else repr(result)[:100]
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:chat:before_print_result","message":"准备打印命令结果","data":{"result_type":result_type_name,"result_type_str":result_type_str,"is_panel":is_panel_check,"result_preview":result_preview},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                        # #endregion
                        # 检查是否是 Panel 对象（使用更严格的检查）
                        is_panel = (
                            hasattr(result, '__class__') and 
                            'Panel' in str(type(result)) and
                            not isinstance(result, str)  # 确保不是字符串
                        )
                        if is_panel:
                            # Panel 对象应该直接使用 console.print 渲染，Rich 会自动处理
                            try:
                                console.print(result)
                            except Exception as print_err:
                                # #region agent log
                                try:
                                    import json
                                    import time
                                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:chat:print_panel_error","message":"打印Panel对象失败","data":{"error":str(print_err),"result_type":type(result).__name__},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                        f.flush()
                                except: pass
                                # #endregion
                                # 如果 Panel 渲染失败，尝试提取内容
                                try:
                                    # Panel 对象有 renderable 属性
                                    if hasattr(result, 'renderable'):
                                        console.print(result.renderable)
                                    else:
                                        console.print(f"[yellow]警告: Panel对象渲染失败，已跳过[/yellow]")
                                except:
                                    console.print(f"[red]无法显示Panel对象: {type(result).__name__}[/red]")
                        else:
                            # 普通字符串或其他对象
                            try:
                                console.print(result)
                            except Exception as print_err:
                                # #region agent log
                                try:
                                    import json
                                    import time
                                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:chat:print_result_error","message":"打印结果失败","data":{"error":str(print_err),"result_type":type(result).__name__},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                        f.flush()
                                except: pass
                                # #endregion
                                # 如果打印失败，尝试转换为字符串
                                try:
                                    console.print(str(result))
                                except:
                                    console.print(f"[red]无法显示结果: {type(result).__name__}[/red]")
                        # 如果命令返回了新的会话 ID，更新当前会话
                        if new_session_id:
                            session_id = new_session_id
                            command_handler.current_session_id = session_id
                            # 立即保存新的会话 ID
                            save_session_id(session_id)
                            console.print(f"[dim]当前会话: {session_id[:8]}...[/dim]")
                        console.print()  # 空行
                        continue  # 命令已处理，跳过正常对话流程
                    else:
                        # result 为 None，说明不是命令或命令返回 None，继续执行正常对话流程
                        # 如果命令返回了新的会话 ID，更新当前会话
                        if new_session_id:
                            session_id = new_session_id
                            command_handler.current_session_id = session_id
                            # 立即保存新的会话 ID
                            save_session_id(session_id)
                            console.print(f"[dim]当前会话: {session_id[:8]}...[/dim]")
                        # 继续执行正常对话流程（不 continue）
                
                # 正常对话流程
                if stream:
                    # 流式响应
                    try:
                        # #region agent log
                        try:
                            import json
                            import time
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:chat:before_asyncio_run","message":"准备调用asyncio.run(_stream_chat)","data":{"message_length":len(msg) if msg else 0},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                        # #endregion
                        
                        try:
                            result = asyncio.run(_stream_chat(client, msg, session_id=session_id))
                            
                            # #region agent log
                            try:
                                import json
                                import time
                                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:chat:after_asyncio_run","message":"asyncio.run完成","data":{"result":result,"result_type":type(result).__name__},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                    f.flush()
                            except: pass
                            # #endregion
                            
                            # 如果 _stream_chat 返回了 Panel 对象，直接打印会导致显示对象表示
                            if result is not None and hasattr(result, '__class__') and 'Panel' in str(type(result)):
                                # #region agent log
                                try:
                                    import json
                                    import time
                                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:chat:panel_result_detected","message":"检测到Panel对象返回值","data":{"result_type":type(result).__name__},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                        f.flush()
                                except: pass
                                # #endregion
                                # Panel 对象不应该作为返回值，转换为字符串或忽略
                                console.print("[yellow]警告: 函数返回了Panel对象，已忽略[/yellow]")
                        except BaseException as be:
                            # 捕获所有异常，包括 SystemExit 和 KeyboardInterrupt
                            # #region agent log
                            try:
                                import json
                                import time
                                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:chat:asyncio_run_baseexception","message":"asyncio.run BaseException","data":{"error_type":type(be).__name__,"error_msg":str(be)[:500],"error_repr":repr(be)[:500],"is_panel":hasattr(be,'__class__') and 'Panel' in str(type(be))},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                    f.flush()
                            except: pass
                            # #endregion
                            # 如果是 Panel 对象异常，转换为普通异常
                            if hasattr(be, '__class__') and 'Panel' in str(type(be)):
                                be = Exception(f"Panel对象异常: {str(be)}")
                            raise
                        
                        # 成功发送消息后，保存会话 ID
                        save_session_id(session_id)
                    except KeyboardInterrupt:
                        # 用户按 Ctrl+C，终止当前对话，继续循环（不退出程序）
                        console.print("\n[dim]对话已终止，输入 /exit 退出程序[/dim]")
                        continue
                    except Exception as e:
                        # #region agent log
                        try:
                            import json
                            import time
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:chat:asyncio_run_exception","message":"asyncio.run异常","data":{"error_type":type(e).__name__,"error_msg":str(e)[:500],"error_repr":repr(e)[:500]},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                        # #endregion
                        # 确保异常对象不是 Panel，如果是则提取错误信息
                        if isinstance(e, Exception):
                            show_error(e)
                        else:
                            # 如果不是异常对象，直接显示
                            try:
                                error_msg = str(e)
                            except:
                                error_msg = repr(e)
                            show_error(Exception(error_msg))
                        continue
                else:
                    # 非流式响应
                    response = client.send(msg, session_id=session_id)
                    # 成功发送消息后，保存会话 ID
                    save_session_id(session_id)
                    # 直接渲染内容，不使用 Panel
                    factory = RendererFactory()
                    renderer = factory.get_renderer(response)
                    rendered = renderer.render(response)
                    
                    # 检查是否为列表（WeatherRenderer 返回列表）
                    if isinstance(rendered, list):
                        for item in rendered:
                            console.print(item)
                    else:
                        console.print(rendered)
                console.print()  # 空行
            except KeyboardInterrupt:
                # 用户按 Ctrl+C，不退出程序，只显示提示
                console.print("\n[dim]提示: 输入 /exit 退出程序[/dim]")
                continue
            except EOFError:
                # 用户按 Ctrl+D，不退出程序，只显示提示
                console.print("\n[dim]提示: 输入 /exit 退出程序[/dim]")
                continue
            except Exception as e:
                show_error(e)
        
        # 保存历史记录
        if readline and history_file:
            try:
                readline.write_history_file(str(history_file))
            except Exception:
                pass
        
        # 退出时保存当前会话 ID
        if session_id:
            save_session_id(session_id)
    
    client.close()

if __name__ == '__main__':
    import sys
    import traceback
    # 设置自定义异常处理器，确保 Panel 对象不会被直接打印
    def custom_excepthook(exc_type, exc_value, exc_traceback):
        """自定义异常处理器，确保异常对象被正确显示"""
        # #region agent log
        try:
            import json
            import time
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:custom_excepthook","message":"未捕获的异常","data":{"exc_type":str(exc_type),"exc_value_type":type(exc_value).__name__,"exc_value_str":str(exc_value)[:500],"is_panel":hasattr(exc_value,'__class__') and 'Panel' in str(type(exc_value))},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        # 如果是 Panel 对象，提取错误信息
        if hasattr(exc_value, '__class__') and 'Panel' in str(type(exc_value)):
            try:
                error_msg = str(exc_value)
            except:
                error_msg = f"Panel对象异常: {type(exc_value).__name__}"
            exc_value = Exception(error_msg)
        
        # 使用 Rich 的 traceback 处理器（如果可用）
        try:
            from rich.traceback import install
            install(show_locals=False)
            from rich.console import Console
            console = Console()
            console.print_exception(show_locals=False)
        except:
            # 如果 Rich 不可用，使用默认的异常处理器
            traceback.print_exception(exc_type, exc_value, exc_traceback)
    
    # 只在交互模式下设置自定义异常处理器
    if sys.stdin.isatty():
        sys.excepthook = custom_excepthook
    
    cli()

