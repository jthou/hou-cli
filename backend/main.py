"""后端服务入口（IPC 服务器）"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI
from backend.api.routes import router
from shared.platform_utils import save_port
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
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console = Console()

app = FastAPI(title="LLM Agent API")
app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}

def find_free_port() -> int:
    """查找可用端口"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def main():
    """启动 IPC 服务器"""
    # 查找可用端口
    port = find_free_port()
    
    # 保存端口号（供前端读取）
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

