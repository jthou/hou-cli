"""后端服务入口（IPC 服务器）"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI
from backend.api.routes import router
from shared.platform_utils import save_port, load_port, get_port_file
from shared.config import Config
from rich.console import Console

# 加载 .env 文件
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

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

app = FastAPI(title="LLM Agent API")

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
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    try:
        # 在启动时尝试初始化 Orchestrator，但不阻塞服务启动
        from backend.core.agent.orchestrator import Orchestrator
        orchestrator = Orchestrator()
        console.print("[green]✓[/green] Orchestrator 初始化成功")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Orchestrator 初始化失败（服务仍可启动）: {str(e)}")
        import logging
        logging.error(f"Orchestrator initialization failed: {str(e)}", exc_info=True)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    """健康检查"""
    try:
        # 简单检查，不依赖任何服务
        return {"status": "ok", "service": "hou-cli-backend"}
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

def is_port_available(port: int) -> bool:
    """检查端口是否可用"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False

def main():
    """启动 IPC 服务器"""
    # 优先从环境变量读取端口配置
    port = None
    
    # 1. 尝试从环境变量读取
    backend_port_str = os.getenv("BACKEND_PORT")
    if backend_port_str:
        try:
            port = int(backend_port_str)
            if not is_port_available(port):
                console.print(f"[yellow]⚠[/yellow] 环境变量中的端口 {port} 不可用，将查找新端口")
                port = None
            else:
                console.print(f"[dim]使用环境变量配置的端口: {port}[/dim]")
        except ValueError:
            console.print(f"[yellow]⚠[/yellow] 环境变量 BACKEND_PORT 值无效: {backend_port_str}")
            port = None
    
    # 2. 如果环境变量未设置或端口不可用，尝试使用之前保存的端口
    if port is None:
        port_file = get_port_file()
        if port_file.exists():
            try:
                saved_port = load_port()
                if is_port_available(saved_port):
                    port = saved_port
                    console.print(f"[dim]使用之前保存的端口: {port}[/dim]")
            except (ValueError, OSError):
                # 端口文件损坏或端口不可用，忽略
                pass
    
    # 3. 如果都没有，查找新端口
    if port is None:
        port = find_free_port()
        console.print(f"[dim]分配新端口: {port}[/dim]")
    
    # 保存端口号（供前端读取，即使从环境变量读取也保存）
    save_port(port)
    
    # 输出环境信息（开发环境）
    if config.is_development:
        console.print(f"[dim]环境: 开发模式[/dim]")
        console.print(f"[dim]调试输出: 已启用[/dim]")
        console.print(f"[dim]日志级别: DEBUG[/dim]\n")
    
    print(f"后端服务启动在 http://127.0.0.1:{port}")
    
    # 启动服务器（仅监听 localhost）
    uvicorn_log_level = "debug" if config.is_development else "info"
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level=uvicorn_log_level
    )

if __name__ == "__main__":
    main()

