# 实现指南

## 概述

本文档提供前后端分离架构的具体实现步骤和代码示例。

## 项目结构

```
hou-cli/
├── frontend/                 # 前端进程
│   ├── __init__.py
│   ├── main.py              # 前端入口
│   ├── ui/                  # Rich UI 组件
│   │   ├── __init__.py
│   │   ├── console.py
│   │   ├── panels.py
│   │   └── progress.py
│   └── client/              # 后端通信客户端
│       ├── __init__.py
│       ├── http_client.py
│       └── websocket_client.py
│
├── backend/                  # 后端进程
│   ├── __init__.py
│   ├── main.py              # 后端入口
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── agent/               # Agent 核心
│   │   ├── __init__.py
│   │   └── agent.py
│   └── services/            # 服务层
│       ├── __init__.py
│       ├── llm_service.py
│       └── tool_service.py
│
├── shared/                   # 共享代码
│   ├── __init__.py
│   ├── models.py
│   └── config.py
│
└── requirements.txt
```

## 步骤 1：创建后端 API 服务器

### 1.1 安装依赖

```bash
pip install fastapi uvicorn websockets httpx
```

### 1.2 创建后端入口

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router

app = FastAPI(
    title="LLM Agent API",
    description="LLM Agent 后端服务",
    version="1.0.0"
)

# 允许跨域（如果需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

### 1.3 创建 API 路由

```python
# backend/api/routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from backend.agent.agent import Agent
from backend.services.llm_service import LLMService

router = APIRouter()
agent = Agent()
llm_service = LLMService()

class ChatRequest(BaseModel):
    message: str
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    status: str = "success"

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求"""
    response = await agent.process(request.message)
    return ChatResponse(response=response)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点，支持流式输出"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 流式处理
            async for chunk in agent.stream_process(data):
                await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
        await websocket.close()
```

### 1.4 创建 Agent 核心

```python
# backend/agent/agent.py
import asyncio
from backend.services.llm_service import LLMService
from backend.services.tool_service import ToolService

class Agent:
    def __init__(self):
        self.llm_service = LLMService()
        self.tool_service = ToolService()
    
    async def process(self, message: str) -> str:
        """处理用户消息"""
        # 1. 调用 LLM 生成响应
        response = await self.llm_service.chat(message)
        return response
    
    async def stream_process(self, message: str):
        """流式处理用户消息"""
        async for chunk in self.llm_service.stream_chat(message):
            yield chunk
```

### 1.5 创建 LLM 服务

```python
# backend/services/llm_service.py
import os
from openai import AsyncOpenAI
from archived.server.src.deepseek_r1 import make_deepseek_client

class LLMService:
    def __init__(self):
        self.client = make_deepseek_client()
    
    async def chat(self, message: str) -> str:
        """同步聊天（非流式）"""
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": message},
            ],
            stream=False
        )
        return response.choices[0].message.content
    
    async def stream_chat(self, message: str):
        """流式聊天"""
        stream = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": message},
            ],
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

## 步骤 2：创建前端 Rich UI

### 2.1 安装依赖

```bash
pip install rich httpx websockets
```

### 2.2 创建 HTTP 客户端

```python
# frontend/client/http_client.py
import httpx
from typing import Optional

class AgentClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def chat(self, message: str) -> str:
        """发送聊天消息"""
        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json={"message": message}
        )
        response.raise_for_status()
        return response.json()["response"]
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
```

### 2.3 创建 WebSocket 客户端

```python
# frontend/client/websocket_client.py
import asyncio
import websockets
from typing import AsyncIterator

class WebSocketClient:
    def __init__(self, uri: str = "ws://localhost:8000/api/ws"):
        self.uri = uri
        self.websocket = None
    
    async def connect(self):
        """连接到 WebSocket 服务器"""
        self.websocket = await websockets.connect(self.uri)
    
    async def send(self, message: str):
        """发送消息"""
        if self.websocket:
            await self.websocket.send(message)
    
    async def receive_stream(self) -> AsyncIterator[str]:
        """接收流式响应"""
        if self.websocket:
            async for message in self.websocket:
                yield message
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
```

### 2.4 创建 Rich UI 组件

```python
# frontend/ui/panels.py
from rich.panel import Panel
from rich.markdown import Markdown
from rich.console import Console

console = Console()

def chat_panel(message: str, role: str = "assistant") -> Panel:
    """创建聊天面板"""
    if role == "user":
        return Panel.fit(
            f"[bold cyan]{message}[/bold cyan]",
            border_style="cyan",
            title="[bold cyan]你[/bold cyan]"
        )
    else:
        return Panel(
            Markdown(message),
            border_style="green",
            title="[bold green]Agent[/bold green]"
        )

def error_panel(error: str) -> Panel:
    """创建错误面板"""
    return Panel(
        f"[bold red]{error}[/bold red]",
        border_style="red",
        title="[bold red]错误[/bold red]"
    )
```

### 2.5 创建前端主程序

```python
# frontend/main.py
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from frontend.client.http_client import AgentClient
from frontend.client.websocket_client import WebSocketClient
from frontend.ui.panels import chat_panel, error_panel

console = Console()

async def main_http():
    """使用 HTTP 客户端的主程序"""
    client = AgentClient()
    
    # 健康检查
    if not await client.health_check():
        console.print(error_panel("无法连接到后端服务"))
        return
    
    console.print(Panel.fit(
        "[bold green]LLM Agent CLI[/bold green]\n"
        "输入 'exit' 或 'quit' 退出",
        border_style="green"
    ))
    
    while True:
        try:
            message = console.input("[bold cyan]你: [/bold cyan]")
            if message.lower() in ["exit", "quit"]:
                break
            
            console.print(chat_panel(message, "user"))
            
            # 显示加载状态
            with console.status("[yellow]思考中...[/yellow]"):
                response = await client.chat(message)
            
            console.print(chat_panel(response, "assistant"))
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(error_panel(str(e)))
    
    await client.close()

async def main_websocket():
    """使用 WebSocket 客户端的主程序（支持流式输出）"""
    client = WebSocketClient()
    
    try:
        await client.connect()
        console.print(Panel.fit(
            "[bold green]LLM Agent CLI (WebSocket)[/bold green]\n"
            "输入 'exit' 或 'quit' 退出",
            border_style="green"
        ))
        
        while True:
            message = console.input("[bold cyan]你: [/bold cyan]")
            if message.lower() in ["exit", "quit"]:
                break
            
            console.print(chat_panel(message, "user"))
            
            # 发送消息
            await client.send(message)
            
            # 流式接收响应
            response_text = Text()
            with Live(response_text, console=console, refresh_per_second=10) as live:
                async for chunk in client.receive_stream():
                    response_text.append(chunk)
                    live.update(response_text)
            
            console.print()  # 换行
        
        await client.close()
    except Exception as e:
        console.print(error_panel(str(e)))

if __name__ == "__main__":
    import sys
    
    # 根据参数选择模式
    if len(sys.argv) > 1 and sys.argv[1] == "--ws":
        asyncio.run(main_websocket())
    else:
        asyncio.run(main_http())
```

## 步骤 3：统一启动脚本

```python
# cli.py
import subprocess
import sys
import time
from multiprocessing import Process
import signal

def start_backend():
    """启动后端进程"""
    subprocess.run([
        sys.executable, "-m", "backend.main"
    ])

def start_frontend():
    """启动前端进程"""
    # 等待后端启动
    time.sleep(2)
    subprocess.run([
        sys.executable, "-m", "frontend.main"
    ])

def signal_handler(sig, frame):
    """处理退出信号"""
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    backend = Process(target=start_backend)
    frontend = Process(target=start_frontend)
    
    backend.start()
    frontend.start()
    
    try:
        backend.join()
        frontend.join()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()
        backend.join()
        frontend.join()
```

## 步骤 4：配置文件

```python
# shared/config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    # 后端配置
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # 前端配置
    frontend_backend_url: str = os.getenv(
        "FRONTEND_BACKEND_URL", 
        "http://localhost:8000"
    )
    
    # LLM 配置
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
    
    # 其他配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
```

## 步骤 5：依赖管理

```txt
# requirements.txt
# 后端依赖
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0
pydantic>=2.0.0

# 前端依赖
rich>=13.7.0
httpx>=0.25.0
websockets>=12.0

# LLM 相关
openai>=1.0.0
langchain>=0.1.0
langchain-ollama>=0.1.0

# 其他
python-dotenv>=1.0.0
```

## 运行和测试

### 开发模式（分别启动）

```bash
# 终端 1：启动后端
python -m backend.main

# 终端 2：启动前端
python -m frontend.main

# 或使用 WebSocket 模式
python -m frontend.main --ws
```

### 生产模式（统一启动）

```bash
python -m cli
```

### 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 聊天请求
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

## 下一步优化

1. **添加认证和授权**
2. **添加日志系统**
3. **添加配置管理**
4. **添加错误处理和重试机制**
5. **添加单元测试和集成测试**
6. **优化性能（连接池、缓存等）**

## 总结

通过以上步骤，你可以实现一个前后端分离的 CLI Agent 工具：

- ✅ 后端独立运行，提供 API 服务
- ✅ 前端独立运行，提供 Rich UI
- ✅ 通过 HTTP/WebSocket 通信
- ✅ 支持流式输出
- ✅ 进程隔离，稳定性高

