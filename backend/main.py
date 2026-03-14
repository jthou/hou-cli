"""后端服务入口 - API + Web UI 统一服务"""
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router
from backend.api.web_routes import router as web_router
from shared.platform_utils import save_port, load_port, get_port_file
from shared.config import Config
from rich.console import Console

# 加载 .env（统一逻辑，见 shared/load_env.py）
from shared.load_env import load_env
load_env(Path(__file__).parent.parent)

# 配置日志系统
config = Config()
log_level = logging.DEBUG if config.is_development else logging.INFO

# 日志文件路径（存储在应用数据目录）
from shared.platform_utils import get_app_data_dir
log_dir = get_app_data_dir() / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "backend.log"

# 配置日志：同时输出到控制台和文件
import logging.handlers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 文件处理器（带日志轮转，每个文件最大10MB，保留5个备份）
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(log_level)
file_handler.setFormatter(formatter)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
console_handler.setFormatter(formatter)

# 配置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# 记录日志文件位置
logging.info(f"日志文件: {log_file}")

console = Console()


@asynccontextmanager
async def _lifespan(app):
    """应用生命周期管理（替代已弃用的 on_event）"""
    # === startup ===
    try:
        worker_enabled = os.getenv("TASK_WORKER_ENABLED", "true").lower() == "true"
        if worker_enabled:
            from backend.infrastructure.execution.task_worker import get_task_worker
            from backend.infrastructure.execution.task_handlers import register_default_handlers
            worker = get_task_worker(
                worker_name="backend-worker",
                poll_interval=int(os.getenv("TASK_WORKER_POLL_INTERVAL", "5")),
                heartbeat_interval=int(os.getenv("TASK_WORKER_HEARTBEAT_INTERVAL", "30"))
            )
            register_default_handlers()
            await worker.start()
            logger.info("任务 Worker 已启动")
    except Exception as e:
        logger.warning(f"启动任务 Worker 失败: {e}，任务队列功能可能不可用")

    errors = []
    deepseek_api_key = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if not deepseek_api_key or len(deepseek_api_key) < 10:
        errors.append("DEEPSEEK_API_KEY 未配置或格式无效")
    bailian = (os.getenv('BAILIAN_API_KEY') or os.getenv('DASHSCOPE_API_KEY') or '').strip()
    if not bailian or len(bailian) < 10:
        errors.append("BAILIAN_API_KEY 或 DASHSCOPE_API_KEY 未配置")
    turbo = os.getenv('TURBOGATEWAY_API_KEY', '').strip()
    if not turbo or len(turbo) < 10:
        errors.append("TURBOGATEWAY_API_KEY 未配置或格式无效")
    # 网页搜索已改为 DuckDuckGo 无头方式，不再依赖 GOOGLE_SEARCH_API_KEY / GOOGLE_SEARCH_ENGINE_ID

    if errors:
        console.print("[bold yellow]⚠️  警告: 发现以下配置问题:[/bold yellow]")
        for err in errors:
            console.print(f"  - {err}")
        console.print("[dim]服务已启动，但部分功能可能不可用。请配置 ~/.config/hou-cli/.env[/dim]\n")
    else:
        console.print("[green]✓[/green] 所有必需的 API 密钥配置有效")
        console.print()

    try:
        from backend.core.agent.orchestrator import Orchestrator
        Orchestrator()
        console.print("[green]✓[/green] Orchestrator 初始化成功")
    except ValueError as e:
        console.print(f"[bold red]✗[/bold red] 配置错误: {str(e)}")
        logging.error(f"Configuration error: {str(e)}", exc_info=True)
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Orchestrator 初始化失败（服务仍可启动）: {str(e)}")
        logging.error(f"Orchestrator initialization failed: {str(e)}", exc_info=True)

    try:
        from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
        hb = get_heartbeat_monitor(interval=int(os.getenv("HEARTBEAT_INTERVAL", "30")))
        await hb.start()
        console.print(f"[green]✓[/green] 心跳监控已启动")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] 心跳监控启动失败: {str(e)}")
        logging.error(f"Heartbeat monitor startup failed: {str(e)}", exc_info=True)

    yield

    # === shutdown ===
    try:
        from backend.infrastructure.execution.task_worker import get_task_worker
        w = get_task_worker()
        if w.is_running:
            await w.stop()
            logger.info("任务 Worker 已停止")
    except Exception as e:
        logger.warning(f"停止任务 Worker 失败: {e}")
    try:
        from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
        await get_heartbeat_monitor().stop()
        logging.info("心跳监控已停止")
    except Exception as e:
        logging.error(f"停止心跳监控失败: {e}", exc_info=True)


app = FastAPI(title="LLM Agent API", lifespan=_lifespan)

# 添加全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    error_trace = traceback.format_exc()
    logger.error(f"Unhandled exception: {str(exc)}\n{error_trace}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": str(exc),
            "detail": "Internal server error. Check server logs for details."
        }
    )

# 延迟加载路由，避免启动时初始化 Orchestrator 失败导致服务无法启动
logger = logging.getLogger(__name__)

# API 路由
app.include_router(router, prefix="/api")

# React SPA 静态资源（必须在 web_router 通配路由之前挂载，否则 /assets/* 会被当成 SPA 路径返回 index.html 导致白屏）
_react_dist = Path(__file__).parent.parent / "frontend" / "web" / "dist"
if _react_dist.exists() and (_react_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_react_dist / "assets")), name="assets")

# Web UI 路由（首页、SPA 回退、WebSocket）
app.include_router(web_router)

@app.get("/health")
async def health():
    """健康检查"""
    try:
        # 简单检查，不依赖任何服务
        from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
        heartbeat_monitor = get_heartbeat_monitor()
        heartbeat_status = heartbeat_monitor.get_status()
        
        return {
            "status": "ok",
            "service": "hou-cli-backend",
            "heartbeat": heartbeat_status
        }
    except Exception as e:
        # 即使出错也返回，避免健康检查本身导致服务不可用
        return {"status": "error", "error": str(e)}

def find_free_port() -> int:
    """查找可用端口"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def is_port_available(port: int, reuse_addr: bool = True) -> bool:
    """检查端口是否可用（可以绑定）。reuse_addr=True 时使用 SO_REUSEADDR，支持 TIME_WAIT 状态下复用。"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if reuse_addr:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False

def is_backend_running_on_port(port: int) -> bool:
    """检查指定端口上是否有后端服务在运行"""
    try:
        import httpx
        response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0, trust_env=False)
        return response.status_code == 200
    except Exception:
        return False

def main():
    """启动服务（API + Web UI，单进程单端口）"""
    port = None
    # 优先使用 WEB_PORT（默认 8081），兼容 BACKEND_PORT
    port_str = os.getenv("WEB_PORT") or os.getenv("BACKEND_PORT")
    
    if port_str:
        try:
            port = int(port_str)
            if not is_port_available(port):
                console.print(f"[yellow]⚠[/yellow] 端口 {port} 不可用")
                port = None
            else:
                console.print(f"[dim]使用端口: {port}[/dim]")
        except ValueError:
            console.print(f"[yellow]⚠[/yellow] 端口配置无效: {port_str}")
            port = None
    
    # 2. 默认 8081，占用时检查是否已为本服务
    if port is None:
        default_port = int(os.getenv("WEB_PORT", "8081"))
        if is_port_available(default_port):
            port = default_port
        elif is_backend_running_on_port(default_port):
            console.print(f"[green]✓[/green] 服务已在 http://127.0.0.1:{default_port} 运行")
            console.print(f"[dim]如需重启，请先运行: python cli.py stop[/dim]")
            return
        else:
            console.print(f"[red]端口 {default_port} 已被占用，请先停止旧进程[/red]")
            console.print(f"[dim]提示: lsof -i :{default_port} 查看占用进程[/dim]")
            raise SystemExit(1)
    
    # 输出环境信息（开发环境）
    if config.is_development:
        console.print(f"[dim]环境: 开发模式[/dim]")
        console.print(f"[dim]调试输出: 已启用[/dim]")
        console.print(f"[dim]日志级别: DEBUG[/dim]\n")
    
    print(f"服务启动在 http://127.0.0.1:{port}")
    print(f"   API: http://127.0.0.1:{port}/api")
    print(f"   Web: http://127.0.0.1:{port}/")
    
    # 保存端口号（供前端读取，在启动前保存，确保前端能立即读取）
    save_port(port)
    
    # 启动服务器（仅监听 localhost）
    uvicorn_log_level = "debug" if config.is_development else "info"
    
    # 启动服务器（不使用 reload 模式，需要手动重启）
    # timeout_graceful_shutdown: 收到 SIGTERM 后最多等待 N 秒即强制退出，释放端口，避免 make start 重启时端口长期占用
    # uvicorn 默认已设置 SO_REUSEADDR，支持端口在 TIME_WAIT 状态下快速复用
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level=uvicorn_log_level,
        timeout_graceful_shutdown=int(os.getenv("UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN", "5")),
    )

if __name__ == "__main__":
    main()

