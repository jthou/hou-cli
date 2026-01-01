"""后端服务入口（IPC 服务器）"""
import os
from pathlib import Path
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI
from backend.api.routes import router
from shared.platform_utils import save_port

# 加载 .env 文件
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

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
    
    print(f"后端服务启动在 http://127.0.0.1:{port}")
    
    # 启动服务器（仅监听 localhost）
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()

