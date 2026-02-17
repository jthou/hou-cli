"""Web 前端服务"""
import os
import asyncio
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from rich.console import Console

# 加载环境变量
PROJECT_ROOT = Path(__file__).parent.parent.parent
from shared.platform_utils import get_app_data_dir

config_dir = Path.home() / ".config" / "hou-cli"
env_paths = [
    config_dir / ".env",
    PROJECT_ROOT / '.env',
    Path.cwd() / '.env',
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

# 创建 FastAPI 应用
app = FastAPI(
    title="Hou CLI Web Interface",
    docs_url=None,  # 禁用自动文档（避免干扰）
    redoc_url=None
)

# 静态文件和模板目录
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

# 确保目录存在
static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)

# 注意：API 路由必须在静态文件挂载之前定义，否则会被静态文件路由覆盖
# 静态文件挂载放在最后

# 模板引擎
try:
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(templates_dir))
except ImportError:
    # 如果 fastapi.templating 不可用，使用 jinja2 直接创建
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    templates = env

# 获取后端服务 URL
def get_backend_url() -> str:
    """获取后端服务 URL"""
    # 优先从环境变量读取
    backend_port = os.getenv("BACKEND_PORT")
    if backend_port:
        return f"http://127.0.0.1:{backend_port}"
    
    # 从端口文件读取
    from shared.platform_utils import load_port
    port = load_port()
    return f"http://127.0.0.1:{port}"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    backend_url = get_backend_url()
    
    # 检查是否是 Jinja2Templates 对象
    if hasattr(templates, 'TemplateResponse'):
        return templates.TemplateResponse("index.html", {
            "request": request,
            "backend_url": backend_url
        })
    else:
        # 使用 jinja2 直接创建的环境
        template = templates.get_template("index.html")
        html = template.render(backend_url=backend_url)
        return HTMLResponse(content=html)


@app.get("/index.html", response_class=HTMLResponse)
async def index_html(request: Request):
    """index.html 路由（兼容浏览器自动补全）"""
    return await index(request)


@app.get("/api/backend-url")
async def get_backend_url_endpoint():
    """获取后端服务 URL"""
    return {"backend_url": get_backend_url()}


@app.get("/api/health")
async def health_proxy():
    """健康检查（代理到后端）"""
    import httpx
    backend_url = get_backend_url()
    
    try:
        async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
            response = await client.get(
                f"{backend_url}/health",
                timeout=5.0
            )
            return response.json()
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接（用于流式聊天）"""
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id")
            
            if not message:
                await websocket.send_json({
                    "type": "error",
                    "content": "消息不能为空"
                })
                continue
            
            # 转发到后端 API
            import httpx
            backend_url = get_backend_url()
            
            try:
                async with httpx.AsyncClient(timeout=300.0, trust_env=False) as client:
                    # 发送流式请求
                    async with client.stream(
                        "POST",
                        f"{backend_url}/api/chat/stream",
                        json={"message": message, "session_id": session_id},
                        timeout=300.0
                    ) as response:
                        if response.status_code != 200:
                            await websocket.send_json({
                                "type": "error",
                                "content": f"后端请求失败: {response.status_code}"
                            })
                            continue
                        
                        # 转发流式响应
                        async for line in response.aiter_lines():
                            if line:
                                # SSE 格式解析
                                if line.startswith("data: "):
                                    content = line[6:]  # 移除 "data: " 前缀
                                    if content == "[DONE]":
                                        await websocket.send_json({
                                            "type": "done"
                                        })
                                        break
                                    else:
                                        await websocket.send_json({
                                            "type": "chunk",
                                            "content": content
                                        })
            except Exception as e:
                logger.error(f"WebSocket 错误: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "content": f"请求失败: {str(e)}"
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket 连接断开")
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}", exc_info=True)


@app.post("/api/chat")
async def chat_api(request: Request):
    """非流式聊天 API（代理到后端）"""
    import httpx
    from pydantic import BaseModel
    
    class ChatRequest(BaseModel):
        message: str
        session_id: Optional[str] = None
    
    data = await request.json()
    chat_request = ChatRequest(**data)
    
    backend_url = get_backend_url()
    
    try:
        async with httpx.AsyncClient(timeout=300.0, trust_env=False) as client:
            response = await client.post(
                f"{backend_url}/api/chat",
                json={
                    "message": chat_request.message,
                    "session_id": chat_request.session_id
                },
                timeout=300.0
            )
            return response.json()
    except Exception as e:
        logger.error(f"聊天请求失败: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/api/storage/config")
async def get_storage_config_proxy():
    """获取存储配置信息（代理到后端）"""
    import httpx
    backend_url = get_backend_url()
    
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(
                f"{backend_url}/api/storage/config",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"后端返回错误: {response.status_code}"
                }
    except httpx.TimeoutException:
        logger.error("获取存储配置超时")
        return {
            "success": False,
            "error": "请求超时"
        }
    except Exception as e:
        logger.error(f"获取存储配置失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/tests/run")
async def run_tests_proxy(request: Request):
    """运行测试（代理到后端）"""
    import httpx
    backend_url = get_backend_url()
    
    try:
        data = await request.json()
        async with httpx.AsyncClient(timeout=600.0, trust_env=False) as client:
            response = await client.post(
                f"{backend_url}/api/tests/run",
                json=data,
                timeout=600.0  # 测试可能需要较长时间
            )
            return response.json()
    except httpx.TimeoutException:
        logger.error("运行测试超时")
        return {
            "success": False,
            "error": "测试运行超时（超过 10 分钟）"
        }
    except Exception as e:
        logger.error(f"运行测试失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/tests/status")
async def get_test_status_proxy():
    """获取测试状态（代理到后端）"""
    import httpx
    backend_url = get_backend_url()
    
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.get(
                f"{backend_url}/api/tests/status",
                timeout=30.0
            )
            return response.json()
    except Exception as e:
        logger.error(f"获取测试状态失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/tests/list")
async def list_tests_proxy():
    """列出测试文件（代理到后端）"""
    import httpx
    backend_url = get_backend_url()
    
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(
                f"{backend_url}/api/tests/list",
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        logger.error(f"列出测试文件失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "tests": []
        }


@app.get("/api/tests/history")
async def get_test_history_proxy(limit: int = 20, offset: int = 0):
    """获取测试历史记录（代理到后端）"""
    import httpx
    backend_url = get_backend_url()
    
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.get(
                f"{backend_url}/api/tests/history",
                params={"limit": str(limit), "offset": str(offset)},
                timeout=30.0
            )
            return response.json()
    except Exception as e:
        logger.error(f"获取测试历史失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/tests/history/{run_id}")
async def get_test_run_detail_proxy(run_id: str):
    """获取测试运行详情（代理到后端）"""
    import httpx
    backend_url = get_backend_url()
    
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.get(
                f"{backend_url}/api/tests/history/{run_id}",
                timeout=30.0
            )
            return response.json()
    except Exception as e:
        logger.error(f"获取测试运行详情失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/tests/statistics")
async def get_test_statistics_proxy():
    """获取测试统计信息（代理到后端）"""
    import httpx
    backend_url = get_backend_url()
    
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.get(
                f"{backend_url}/api/tests/statistics",
                timeout=30.0
            )
            return response.json()
    except Exception as e:
        logger.error(f"获取测试统计失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# 在所有 API 路由定义之后挂载静态文件
# 这样可以确保 API 路由优先匹配
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def find_free_port(start_port: int = 8080) -> int:
    """查找可用端口"""
    import socket
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError("无法找到可用端口")


def main():
    """启动 Web 前端服务"""
    # 获取端口（默认使用 8081，避免与 Docker 等服务冲突）
    default_port = int(os.getenv("WEB_PORT", "8081"))
    web_port = default_port
    
    # 检查端口是否可用
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', web_port))
    except OSError:
        # 端口被占用，查找新端口
        web_port = find_free_port(web_port)
        if web_port != default_port:
            console.print(f"[yellow]⚠ 端口 {default_port} 被占用，使用新端口: {web_port}[/yellow]")
    
    console.print(f"[green]🌐 Web 前端服务启动在 http://127.0.0.1:{web_port}[/green]")
    console.print(f"[dim]后端服务: {get_backend_url()}[/dim]")
    
    # 启动服务器
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=web_port,
        log_level="info"
    )


if __name__ == "__main__":
    main()

