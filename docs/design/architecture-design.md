# LLM Agent CLI 架构设计文档

## 概述

本文档说明 LLM Agent CLI 工具的架构设计，参考 Cursor Agent 的设计模式，采用**前后端分离架构**。

**核心设计原则**：
- ✅ **前后端分离**：前端（Rich UI）和后端（Agent 服务）运行在不同进程中
- ✅ **进程隔离**：前端负责用户交互，后端负责业务逻辑和 LLM 调用
- ✅ **异步通信**：通过进程间通信（IPC）进行通信
- ✅ **可扩展性**：后端可以独立扩展，支持多客户端连接

## 核心问题：为什么需要前后端分离？

### 简短回答

**对于类似 Cursor Agent 的复杂 CLI 工具：需要前后端分离架构**

前后端分离的必要性：
1. **进程隔离**：前端 UI 进程和后端 Agent 进程分离，互不影响
2. **稳定性**：后端崩溃不会导致前端 UI 崩溃
3. **可扩展性**：后端可以独立扩展，支持多客户端
4. **资源管理**：后端可以独立管理 LLM 连接、工具执行等资源
5. **并发处理**：后端可以处理多个并发请求

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     用户终端                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  前端进程 (Frontend Process)                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Rich UI 层                                      │  │
│  │  - 表格、面板、进度条                            │  │
│  │  - 用户输入/输出                                 │  │
│  │  - 交互式界面                                    │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  前端通信层                                      │  │
│  │  - IPC Client (TCP Localhost)                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                    IPC (TCP Localhost)
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  后端进程 (Backend Process / Agent Service)            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  IPC 服务器层                                    │  │
│  │  - FastAPI (TCP Localhost)                      │  │
│  │  - 本地端口监听                                  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  流程识别和编排层                                 │  │
│  │  - Workflow Identifier (流程识别)                │  │
│  │  - Workflow Engine (SOP流程执行)                │  │
│  │  - Orchestrator (动态编排)                       │  │
│  │  - Coordinator (Agent协调)                       │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  多 Agent 协作层                                 │  │
│  │  - Chat Agent (对话)                            │  │
│  │  - PDF Agent (文档处理)                         │  │
│  │  - Code Agent (代码生成/编辑)                    │  │
│  │  - FileSystem Agent (文件系统操作)               │  │
│  │  - Research Agent (研究)                         │  │
│  │  - Tool Agent (工具调用)                        │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  长记忆和上下文管理                              │  │
│  │  - 长记忆存储 (Long-term Memory)                 │  │
│  │  - 上下文管理器 (Context Manager)               │  │
│  │  - 会话历史管理                                  │  │
│  │  - 代码上下文缓存                                │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Agent 状态管理                                  │  │
│  │  - 共享状态                                      │  │
│  │  - 消息传递                                      │  │
│  │  - 事件系统                                      │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  LLM 服务层                                     │  │
│  │  - DeepSeek API 客户端                          │  │
│  │  - Ollama 客户端                                 │  │
│  │  - 流式响应处理                                  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  代码执行层                                      │  │
│  │  - 代码执行引擎                                  │  │
│  │  - 多语言支持 (Python/Shell/等)                 │  │
│  │  - 执行结果捕获                                  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  安全执行层                                      │  │
│  │  - 沙箱隔离                                      │  │
│  │  - 权限控制                                      │  │
│  │  - 命令白名单/黑名单                             │  │
│  │  - 资源限制                                      │  │
│  │  - 执行审计                                      │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  工具执行层                                      │  │
│  │  - PDF 处理                                      │  │
│  │  - 文件操作                                      │  │
│  │  - 外部工具调用                                  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  知识库管理层                                    │  │
│  │  - 文件存储管理 (临时/存档)                      │  │
│  │  - 知识提炼和处理                                │  │
│  │  - 向量化存储                                     │  │
│  │  - 向量搜索服务                                  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  存储层                                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  文件存储                                          │  │
│  │  - 临时文件区域 (temp/)                           │  │
│  │  - 知识存档区域 (archive/)                        │  │
│  │  - 原始文件存储                                   │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  向量数据库                                       │  │
│  │  - Chroma / FAISS / Qdrant                        │  │
│  │  - 向量索引                                       │  │
│  │  - 元数据管理                                     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  外部服务                                                │
│  - DeepSeek API                                         │
│  - Ollama (本地)                                        │
│  - 其他工具/服务                                        │
└─────────────────────────────────────────────────────────┘
```

### 进程模型

```
进程 1: 前端进程 (Frontend)
├── Rich UI 渲染
├── 用户交互处理
└── 与后端通信

进程 2: 后端进程 (Backend/Agent Service)
├── API 服务器
├── Agent 逻辑
├── LLM 调用
└── 工具执行
```

**关键点**：
- ✅ 两个独立的进程
- ✅ 通过 IPC (TCP Localhost) 通信
- ✅ 前端可以重启而不影响后端
- ✅ 后端可以服务多个前端客户端

## 通信方式：IPC (TCP Localhost)

**已选择：IPC 通信方式**

**优点**：
- ✅ 低延迟
- ✅ 无需网络端口
- ✅ 适合单机部署
- ✅ 跨平台支持（Windows、Mac、Linux）
- ✅ 可打包成安装程序

**缺点**：
- ❌ 只支持本地通信

**实现方案：TCP Localhost**

使用本地 TCP 连接，跨平台兼容性最好。详细实现请参考：[ipc-and-packaging.md](./ipc-and-packaging.md)

**选择理由**：
- ✅ 跨平台兼容性最好（Windows、Mac、Linux）
- ✅ 实现简单，易于维护
- ✅ 支持流式输出
- ✅ 易于调试和测试
- ✅ 打包后稳定可靠
- ✅ 无需额外的 IPC 库依赖

详细实现请参考：[ipc-and-packaging.md](./ipc-and-packaging.md)

## 目录结构建议

```
hou-cli/
├── frontend/                 # 前端进程（CLI 用户界面）
│   ├── __init__.py
│   ├── main.py              # CLI 入口（前端主程序）
│   ├── ui/                  # Rich UI 组件
│   │   ├── __init__.py
│   │   ├── console.py       # Console 管理
│   │   ├── panels.py        # 面板组件
│   │   ├── tables.py        # 表格组件
│   │   └── progress.py      # 进度条组件
│   └── client/              # 后端通信客户端
│       ├── __init__.py
│       └── ipc_client.py    # IPC 客户端 (TCP Localhost)
│
├── backend/                  # 后端进程（Agent 服务）
│   ├── __init__.py
│   ├── main.py              # 后端服务入口（IPC 服务器）
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   └── routes.py        # 路由定义
│   ├── agent/               # Agent 核心逻辑
│   │   ├── __init__.py
│   │   ├── orchestrator.py  # Agent 编排器
│   │   ├── coordinator.py   # Agent 协调器
│   │   ├── base_agent.py   # Agent 基类
│   │   ├── agents/          # 具体Agent实现
│   │   │   ├── __init__.py
│   │   │   ├── chat_agent.py
│   │   │   ├── pdf_agent.py
│   │   │   ├── code_agent.py
│   │   │   ├── filesystem_agent.py
│   │   │   └── ...
│   │   ├── planner.py       # 任务规划
│   │   ├── executor.py      # 任务执行
│   │   └── state.py         # 状态管理
│   ├── workflow/            # SOP 流程编排
│   │   ├── __init__.py
│   │   ├── workflow_engine.py
│   │   ├── workflow_identifier.py
│   │   └── workflow_state.py
│   ├── memory/              # 长记忆和上下文管理
│   │   ├── __init__.py
│   │   ├── long_term_memory.py
│   │   ├── context_manager.py
│   │   ├── session_history.py
│   │   └── code_context.py
│   ├── knowledge/           # 知识库管理
│   │   ├── __init__.py
│   │   ├── storage.py      # 文件存储管理
│   │   ├── processor.py    # 知识提炼处理
│   │   ├── vector_store.py # 向量存储服务
│   │   ├── search.py       # 向量搜索服务
│   │   └── indexer.py      # 知识索引管理
│   ├── execution/           # 代码执行
│   │   ├── __init__.py
│   │   ├── executor.py     # 代码执行引擎
│   │   ├── secure_executor.py # 安全执行包装器
│   │   └── result_handler.py # 执行结果处理
│   ├── security/            # 安全机制
│   │   ├── __init__.py
│   │   ├── sandbox.py       # 沙箱隔离
│   │   ├── permission_manager.py # 权限管理
│   │   ├── command_filter.py # 命令过滤
│   │   ├── resource_limiter.py # 资源限制
│   │   └── audit_logger.py  # 审计日志
│   └── services/            # 服务层
│       ├── __init__.py
│       ├── llm_service.py   # LLM 服务
│       └── tool_service.py  # 工具服务
│
├── shared/                   # 共享代码
│   ├── __init__.py
│   ├── models.py            # 数据模型
│   ├── config.py            # 配置管理
│   ├── platform_utils.py    # 平台工具函数
│   └── utils.py             # 工具函数
│
├── workflows/               # SOP 流程定义文件
│   ├── pdf_analysis_sop.yaml
│   ├── code_review_sop.yaml
│   └── ...
│
├── data/                     # 数据存储目录（运行时创建）
│   ├── temp/                # 临时文件区域
│   ├── archive/             # 知识存档区域
│   ├── vectors/             # 向量数据库
│   └── metadata/            # 元数据存储
│
├── cli.py                    # 统一启动脚本（可选，生产模式）
│
├── archived/                 # 归档目录
│   └── server/src/          # 原有代码（逐步迁移）
│       ├── deepseek_r1.py
│       ├── dynamic_prompt.py
│       └── pdf_langchains.py
│
└── docs/                    # 文档
```

## CLI 入口说明

### CLI 组织方式

**推荐方案：前端即 CLI**

- **`frontend/main.py`**：CLI 主入口
  - 包含 Rich UI 和用户交互逻辑
  - 通过 IPC 客户端与后端通信
  - 用户直接运行的就是这个文件

- **`backend/main.py`**：后端服务入口
  - 启动 IPC 服务器（FastAPI）
  - 运行 Agent 服务

- **`cli.py`**：统一启动脚本（可选）
  - 用于生产模式，同时启动前后端
  - 开发模式可以分别启动

### 使用方式

**开发模式**（分别启动）：
```bash
# 终端 1：启动后端
python -m backend.main

# 终端 2：启动前端 CLI
python -m frontend.main
```

**生产模式**（统一启动）：
```bash
# 自动启动前后端
python cli.py
```

**安装后使用**（如果打包成包）：
```bash
# 安装后
pip install -e .

# 使用 CLI
hou-cli  # 或 python -m frontend.main
```

## 实现步骤

### 阶段 1：后端 API 服务器

1. **创建 FastAPI 后端**
   ```python
   # backend/main.py
   from fastapi import FastAPI
   from backend.api.routes import router
   
   app = FastAPI(title="LLM Agent API")
   app.include_router(router)
   
   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)
   ```

2. **迁移现有功能到后端**
   - 将 `archived/server/src/` 中的功能迁移到 `backend/services/`
   - 封装为服务类
   - 提供 API 接口

### 阶段 2：前端 Rich UI

1. **创建前端入口**
   ```python
   # frontend/main.py
   from rich.console import Console
   from frontend.client.http_client import AgentClient
   from frontend.ui.panels import ChatPanel
   
   console = Console()
   client = AgentClient("http://localhost:8000")
   
   def main():
       while True:
           message = console.input("[bold cyan]你: [/bold cyan]")
           response = client.chat(message)
           console.print(ChatPanel(response))
   ```

2. **实现 Rich UI 组件**
   - 聊天界面
   - 进度显示
   - 结果展示

### 阶段 3：集成和优化

1. **错误处理和重连机制**
2. **配置管理**
3. **日志系统**
4. **流式输出支持**（通过 HTTP 长连接）

## 启动方式

### 方式 1：分别启动（开发模式）

```bash
# 终端 1：启动后端服务
python -m backend.main

# 终端 2：启动前端 CLI
python -m frontend.main
```

### 方式 2：统一启动（生产模式）

```python
# cli.py - 统一启动脚本
import subprocess
import sys
import time
from multiprocessing import Process
import signal

def start_backend():
    """启动后端进程"""
    subprocess.run([sys.executable, "-m", "backend.main"])

def start_frontend():
    """启动前端进程（CLI）"""
    # 等待后端启动
    time.sleep(2)
    subprocess.run([sys.executable, "-m", "frontend.main"])

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

**使用方式**：
```bash
# 统一启动（自动启动前后端）
python cli.py
```

## 与 Cursor Agent 的对比

| 特性 | Cursor Agent | 本项目 |
|------|-------------|--------|
| 前端 | Electron/Web UI | Rich UI (终端) |
| 后端 | 独立服务进程 | 独立服务进程 |
| 通信 | IPC (TCP Localhost) | IPC (TCP Localhost) |
| 进程隔离 | ✅ 是 | ✅ 是 |
| 可扩展性 | ✅ 支持多客户端 | ✅ 支持多客户端 |
| 流式输出 | ✅ 支持 | ✅ 支持 |

## 优势总结

### 前后端分离的优势

1. **稳定性**
   - 后端崩溃不影响前端 UI
   - 前端可以独立重启
   - 错误隔离

2. **可扩展性**
   - 后端可以独立扩展（多进程、多线程）
   - 支持多个前端客户端
   - 可以添加其他类型的客户端（Web UI、API 客户端等）

3. **资源管理**
   - 后端统一管理 LLM 连接池
   - 统一管理工具执行
   - 更好的资源利用

4. **开发效率**
   - 前后端可以独立开发
   - 可以独立测试
   - 可以独立部署

5. **用户体验**
   - 前端 UI 响应快速（不阻塞）
   - 后端可以异步处理长时间任务
   - 支持实时流式输出

## 多 Agent 协作架构

### 概述

对于复杂任务，系统支持**多 Agent 协作**模式。多个专门的 Agent 可以协同工作，各自负责不同的子任务，最终完成复杂的任务。

### 架构设计

```
用户请求
    ↓
Agent 编排器 (Orchestrator)
    ├── 任务分解
    ├── Agent 选择
    └── 结果聚合
    ↓
┌─────────────────────────────────────────┐
│  多个专门化的 Agent                     │
├─────────────────────────────────────────┤
│  Chat Agent      → 对话和问答           │
│  PDF Agent       → PDF 处理和分析       │
│  Code Agent      → 代码生成和修改        │
│  Research Agent  → 信息检索和研究       │
│  Tool Agent      → 工具调用和执行        │
└─────────────────────────────────────────┘
    ↓
结果聚合和返回
```

### Agent 编排器 (Orchestrator)

编排器负责：
1. **任务分析**：理解用户请求的复杂性
2. **任务分解**：将复杂任务分解为子任务
3. **Agent 选择**：为每个子任务选择合适的 Agent
4. **执行协调**：协调多个 Agent 的执行顺序
5. **结果聚合**：合并多个 Agent 的结果

```python
# backend/agent/orchestrator.py
from typing import List, Dict, Any
from backend.agent.agents.chat_agent import ChatAgent
from backend.agent.agents.pdf_agent import PDFAgent
from backend.agent.agents.code_agent import CodeAgent
from backend.agent.coordinator import AgentCoordinator

class Orchestrator:
    def __init__(self):
        self.agents = {
            "chat": ChatAgent(),
            "pdf": PDFAgent(),
            "code": CodeAgent(),
            # ... 其他 Agent
        }
        self.coordinator = AgentCoordinator()
    
    async def process(self, task: str) -> str:
        """处理复杂任务"""
        # 1. 任务分析
        task_plan = await self.analyze_task(task)
        
        # 2. 任务分解
        subtasks = self.decompose_task(task_plan)
        
        # 3. Agent 选择和协调执行
        results = await self.coordinator.execute(subtasks)
        
        # 4. 结果聚合
        final_result = self.aggregate_results(results)
        
        return final_result
    
    async def analyze_task(self, task: str) -> Dict[str, Any]:
        """分析任务，确定需要的 Agent"""
        # 使用 LLM 分析任务
        analysis = await self.llm_service.analyze(task)
        return analysis
    
    def decompose_task(self, task_plan: Dict) -> List[Dict]:
        """将任务分解为子任务"""
        subtasks = []
        # 根据任务计划创建子任务
        return subtasks
```

### Agent 协调器 (Coordinator)

协调器负责管理多个 Agent 的执行：

```python
# backend/agent/coordinator.py
import asyncio
from typing import List, Dict, Any
from enum import Enum

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"      # 并行执行
    PIPELINE = "pipeline"      # 流水线执行

class AgentCoordinator:
    def __init__(self):
        self.execution_history = []
    
    async def execute(
        self, 
        subtasks: List[Dict],
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    ) -> List[Dict]:
        """执行多个子任务"""
        if mode == ExecutionMode.SEQUENTIAL:
            return await self._execute_sequential(subtasks)
        elif mode == ExecutionMode.PARALLEL:
            return await self._execute_parallel(subtasks)
        elif mode == ExecutionMode.PIPELINE:
            return await self._execute_pipeline(subtasks)
    
    async def _execute_sequential(self, subtasks: List[Dict]) -> List[Dict]:
        """顺序执行"""
        results = []
        for subtask in subtasks:
            agent = self._get_agent(subtask["agent_type"])
            result = await agent.execute(subtask["task"])
            results.append({
                "subtask": subtask,
                "result": result,
                "agent": subtask["agent_type"]
            })
        return results
    
    async def _execute_parallel(self, subtasks: List[Dict]) -> List[Dict]:
        """并行执行"""
        tasks = []
        for subtask in subtasks:
            agent = self._get_agent(subtask["agent_type"])
            tasks.append(agent.execute(subtask["task"]))
        
        results = await asyncio.gather(*tasks)
        return [
            {"subtask": st, "result": r, "agent": st["agent_type"]}
            for st, r in zip(subtasks, results)
        ]
    
    async def _execute_pipeline(self, subtasks: List[Dict]) -> List[Dict]:
        """流水线执行（前一个的输出作为后一个的输入）"""
        results = []
        previous_result = None
        
        for subtask in subtasks:
            agent = self._get_agent(subtask["agent_type"])
            
            # 如果有前一个结果，合并到当前任务
            if previous_result:
                subtask["context"] = previous_result
            
            result = await agent.execute(subtask["task"])
            results.append({
                "subtask": subtask,
                "result": result,
                "agent": subtask["agent_type"]
            })
            previous_result = result
        
        return results
```

### 专门化的 Agent

每个 Agent 专注于特定领域：

```python
# backend/agent/agents/base_agent.py
from abc import ABC, abstractmethod
from backend.services.llm_service import LLMService

class BaseAgent(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.llm_service = LLMService()
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Any:
        """执行任务"""
        pass
    
    async def think(self, prompt: str) -> str:
        """Agent 思考过程"""
        system_prompt = f"""你是 {self.name}，{self.description}
请仔细思考并执行任务。"""
        
        response = await self.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=prompt
        )
        return response

# backend/agent/agents/pdf_agent.py
from backend.agent.agents.base_agent import BaseAgent
from backend.services.tool_service import ToolService

class PDFAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="PDF处理Agent",
            description="专门处理PDF文档的读取、分析和总结"
        )
        self.tool_service = ToolService()
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行PDF处理任务"""
        file_path = task.get("file_path")
        operation = task.get("operation", "summarize")
        
        if operation == "summarize":
            result = await self.tool_service.summarize_pdf(file_path)
        elif operation == "extract":
            result = await self.tool_service.extract_text(file_path)
        else:
            result = await self.tool_service.process_pdf(file_path, operation)
        
        return {
            "agent": self.name,
            "operation": operation,
            "result": result
        }

# backend/agent/agents/code_agent.py
from backend.agent.agents.base_agent import BaseAgent

class CodeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="代码生成Agent",
            description="专门处理代码生成、修改和优化"
        )
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行代码相关任务"""
        code_task = task.get("task")
        language = task.get("language", "python")
        
        # 使用LLM生成或修改代码
        result = await self.think(
            f"请帮我完成以下代码任务（使用{language}）：{code_task}"
        )
        
        return {
            "agent": self.name,
            "code": result,
            "language": language
        }
```

### 多 Agent 协作示例

#### 示例 1：复杂任务处理

```python
# 用户请求："分析这个PDF文件，然后根据内容生成Python代码"

# 1. Orchestrator 分析任务
task_plan = {
    "agents_needed": ["pdf", "code"],
    "execution_mode": "pipeline",  # 流水线：先PDF分析，再代码生成
    "subtasks": [
        {
            "agent_type": "pdf",
            "task": {"file_path": "document.pdf", "operation": "analyze"}
        },
        {
            "agent_type": "code",
            "task": {"task": "根据PDF分析结果生成代码", "language": "python"}
        }
    ]
}

# 2. Coordinator 协调执行
results = await coordinator.execute(
    task_plan["subtasks"],
    mode=ExecutionMode.PIPELINE
)

# 3. 结果聚合
final_result = f"""
PDF分析结果：{results[0]['result']}
生成的代码：{results[1]['code']}
"""
```

#### 示例 2：并行任务处理

```python
# 用户请求："同时分析这两个PDF文件，然后对比结果"

task_plan = {
    "agents_needed": ["pdf", "chat"],
    "execution_mode": "parallel",  # 并行处理两个PDF
    "subtasks": [
        {"agent_type": "pdf", "task": {"file_path": "doc1.pdf"}},
        {"agent_type": "pdf", "task": {"file_path": "doc2.pdf"}}
    ],
    "aggregation": {
        "agent_type": "chat",
        "task": "对比两个PDF的分析结果"
    }
}

# 并行执行
pdf_results = await coordinator.execute(
    task_plan["subtasks"],
    mode=ExecutionMode.PARALLEL
)

# 聚合结果
comparison = await chat_agent.execute({
    "task": f"对比以下两个分析结果：\n1. {pdf_results[0]}\n2. {pdf_results[1]}"
})
```

### Agent 通信机制

Agent 之间可以通过以下方式通信：

1. **共享状态**：通过状态管理器共享信息
2. **消息传递**：Agent 之间直接传递消息
3. **事件驱动**：通过事件系统进行异步通信

```python
# backend/agent/state.py
from typing import Dict, Any
import asyncio

class AgentState:
    def __init__(self):
        self.shared_data: Dict[str, Any] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.event_handlers: Dict[str, List] = {}
    
    def set_shared_data(self, key: str, value: Any):
        """设置共享数据"""
        self.shared_data[key] = value
    
    def get_shared_data(self, key: str) -> Any:
        """获取共享数据"""
        return self.shared_data.get(key)
    
    async def send_message(self, from_agent: str, to_agent: str, message: Any):
        """Agent 之间发送消息"""
        await self.message_queue.put({
            "from": from_agent,
            "to": to_agent,
            "message": message
        })
    
    async def receive_message(self, agent_name: str) -> Dict:
        """接收消息"""
        message = await self.message_queue.get()
        if message["to"] == agent_name:
            return message
        else:
            # 放回队列
            await self.message_queue.put(message)
            return None
```

### 目录结构更新

```
backend/
├── agent/
│   ├── orchestrator.py      # Agent 编排器（主入口）
│   ├── coordinator.py       # Agent 协调器（执行管理）
│   ├── base_agent.py        # Agent 基类
│   ├── agents/              # 具体Agent实现
│   │   ├── __init__.py
│   │   ├── chat_agent.py    # 对话Agent
│   │   ├── pdf_agent.py     # PDF处理Agent
│   │   ├── code_agent.py    # 代码生成/编辑Agent
│   │   ├── filesystem_agent.py # 文件系统操作Agent
│   │   ├── research_agent.py # 研究Agent
│   │   └── tool_agent.py    # 工具调用Agent
│   ├── memory/              # 长记忆和上下文管理
│   │   ├── __init__.py
│   │   ├── long_term_memory.py # 长记忆存储
│   │   ├── context_manager.py  # 上下文管理器
│   │   ├── session_history.py  # 会话历史
│   │   └── code_context.py    # 代码上下文缓存
│   ├── planner.py           # 任务规划
│   ├── executor.py          # 任务执行
│   └── state.py             # 状态管理（Agent间通信）
```

### 多 Agent 协作的优势

1. **专业化分工**
   - 每个 Agent 专注于特定领域
   - 提高任务处理质量和效率
   - 易于维护和扩展

2. **灵活组合**
   - 根据任务需求动态选择 Agent
   - 支持多种执行模式（顺序、并行、流水线）
   - 可以处理复杂的多步骤任务

3. **可扩展性**
   - 易于添加新的专门化 Agent
   - 不影响现有 Agent 的功能
   - 支持插件化架构

4. **容错性**
   - 单个 Agent 失败不影响其他 Agent
   - 可以重试失败的子任务
   - 支持部分结果返回

### 扩展新的 Agent

添加新的 Agent 非常简单：

```python
# backend/agent/agents/custom_agent.py
from backend.agent.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="自定义Agent",
            description="你的Agent描述"
        )
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """实现你的Agent逻辑"""
        # 你的实现
        return result

# 在 Orchestrator 中注册
class Orchestrator:
    def __init__(self):
        self.agents = {
            "chat": ChatAgent(),
            "pdf": PDFAgent(),
            "code": CodeAgent(),
            "custom": CustomAgent(),  # 添加新Agent
        }
```

## SOP 流程编排架构

### 概述

对于需要按照标准流程执行的任务，系统支持 **SOP (Standard Operating Procedure)** 流程编排。SOP 定义了预定义的工作流程，确保任务按照标准步骤执行，提高一致性和可重复性。

### 为什么需要 SOP？

1. **标准化流程**：某些任务需要按照固定步骤执行
2. **可重复性**：确保相同任务每次执行方式一致
3. **质量控制**：通过预定义流程保证质量
4. **效率提升**：避免每次都重新分析和规划
5. **合规性**：满足特定行业或场景的合规要求

### 架构设计

```
用户请求
    ↓
流程识别器 (Workflow Identifier)
    ├── 识别任务类型
    ├── 匹配 SOP 模板
    └── 选择执行模式
    ↓
┌─────────────────────────────────────────┐
│  执行模式选择                            │
├─────────────────────────────────────────┤
│  1. SOP 流程执行 (预定义流程)            │
│  2. 动态编排执行 (Orchestrator)         │
└─────────────────────────────────────────┘
    ↓ (SOP 模式)
流程执行引擎 (Workflow Engine)
    ├── 加载 SOP 定义
    ├── 执行流程步骤
    ├── 条件判断和分支
    └── 错误处理和重试
    ↓
Agent 执行
    ↓
结果收集和验证
```

### SOP 流程定义

SOP 可以通过 YAML 或 JSON 定义：

```yaml
# workflows/pdf_analysis_sop.yaml
name: PDF分析标准流程
version: 1.0
description: 标准化的PDF文档分析流程

steps:
  - id: step1
    name: 文档加载
    agent: pdf
    action: load
    params:
      file_path: ${input.file_path}
    timeout: 30
    
  - id: step2
    name: 文本提取
    agent: pdf
    action: extract_text
    depends_on: [step1]
    params:
      document_id: ${step1.result.document_id}
    
  - id: step3
    name: 内容分析
    agent: chat
    action: analyze
    depends_on: [step2]
    params:
      text: ${step2.result.text}
      analysis_type: comprehensive
    
  - id: step4
    name: 生成摘要
    agent: chat
    action: summarize
    depends_on: [step3]
    params:
      analysis_result: ${step3.result}
    
  - id: step5
    name: 结果验证
    condition: ${step4.result.length > 100}
    on_true:
      - agent: chat
        action: format_output
        params:
          summary: ${step4.result}
    on_false:
      - agent: chat
        action: retry_summarize
        params:
          analysis_result: ${step3.result}

output:
  summary: ${step4.result}
  analysis: ${step3.result}
  metadata:
    document_id: ${step1.result.document_id}
    processed_at: ${timestamp}
```

### 流程执行引擎

```python
# backend/workflow/workflow_engine.py
from typing import Dict, Any, List, Optional
import yaml
from pathlib import Path
from backend.agent.orchestrator import Orchestrator
from backend.workflow.workflow_state import WorkflowState

class WorkflowEngine:
    """SOP 流程执行引擎"""
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.workflows = {}  # 缓存的流程定义
        self.state = WorkflowState()
    
    async def execute_workflow(
        self, 
        workflow_name: str, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行 SOP 流程
        
        Args:
            workflow_name: 流程名称
            input_data: 输入数据
        
        Returns:
            执行结果
        """
        # 1. 加载流程定义
        workflow_def = await self.load_workflow(workflow_name)
        
        # 2. 初始化流程状态
        self.state.init(workflow_def, input_data)
        
        # 3. 执行流程步骤
        for step in workflow_def["steps"]:
            await self.execute_step(step)
        
        # 4. 收集输出
        output = self.collect_output(workflow_def)
        
        return output
    
    async def load_workflow(self, workflow_name: str) -> Dict:
        """加载流程定义"""
        if workflow_name in self.workflows:
            return self.workflows[workflow_name]
        
        # 从文件加载
        workflow_path = Path(f"workflows/{workflow_name}.yaml")
        with open(workflow_path) as f:
            workflow_def = yaml.safe_load(f)
        
        self.workflows[workflow_name] = workflow_def
        return workflow_def
    
    async def execute_step(self, step: Dict):
        """执行单个步骤"""
        step_id = step["id"]
        
        # 检查依赖
        if not self.check_dependencies(step):
            raise Exception(f"Step {step_id} dependencies not met")
        
        # 解析参数（支持变量替换）
        params = self.resolve_params(step.get("params", {}))
        
        # 执行 Agent 任务
        agent_name = step["agent"]
        action = step["action"]
        
        task = {
            "action": action,
            **params
        }
        
        try:
            result = await self.orchestrator.agents[agent_name].execute(task)
            
            # 保存步骤结果
            self.state.set_step_result(step_id, result)
            
        except Exception as e:
            # 错误处理
            if step.get("retry", False):
                # 重试逻辑
                result = await self.retry_step(step, e)
                self.state.set_step_result(step_id, result)
            else:
                raise
    
    def check_dependencies(self, step: Dict) -> bool:
        """检查步骤依赖"""
        depends_on = step.get("depends_on", [])
        for dep in depends_on:
            if not self.state.has_step_result(dep):
                return False
        return True
    
    def resolve_params(self, params: Dict) -> Dict:
        """解析参数，支持变量替换"""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${"):
                # 变量替换：${step1.result.field}
                resolved[key] = self.state.resolve_variable(value)
            else:
                resolved[key] = value
        return resolved
    
    def collect_output(self, workflow_def: Dict) -> Dict:
        """收集流程输出"""
        output_spec = workflow_def.get("output", {})
        output = {}
        
        for key, value_template in output_spec.items():
            if isinstance(value_template, str) and value_template.startswith("${"):
                output[key] = self.state.resolve_variable(value_template)
            elif isinstance(value_template, dict):
                output[key] = {
                    k: self.state.resolve_variable(v) 
                    if isinstance(v, str) and v.startswith("${") 
                    else v
                    for k, v in value_template.items()
                }
            else:
                output[key] = value_template
        
        return output
```

### 流程状态管理

```python
# backend/workflow/workflow_state.py
from typing import Dict, Any, Optional
import re
from datetime import datetime

class WorkflowState:
    """流程状态管理"""
    
    def __init__(self):
        self.input_data: Dict[str, Any] = {}
        self.step_results: Dict[str, Any] = {}
        self.workflow_def: Optional[Dict] = None
        self.variables: Dict[str, Any] = {}
    
    def init(self, workflow_def: Dict, input_data: Dict):
        """初始化流程状态"""
        self.workflow_def = workflow_def
        self.input_data = input_data
        self.step_results = {}
        self.variables = {
            "input": input_data,
            "timestamp": datetime.now().isoformat()
        }
    
    def set_step_result(self, step_id: str, result: Any):
        """保存步骤结果"""
        self.step_results[step_id] = result
        self.variables[step_id] = {"result": result}
    
    def has_step_result(self, step_id: str) -> bool:
        """检查步骤是否已完成"""
        return step_id in self.step_results
    
    def get_step_result(self, step_id: str) -> Any:
        """获取步骤结果"""
        return self.step_results.get(step_id)
    
    def resolve_variable(self, variable_expr: str) -> Any:
        """
        解析变量表达式
        支持格式：${step1.result.field} 或 ${input.field}
        """
        # 提取变量路径：${step1.result.field} -> step1.result.field
        match = re.match(r'\$\{([^}]+)\}', variable_expr)
        if not match:
            return variable_expr
        
        path = match.group(1)
        parts = path.split('.')
        
        # 从 variables 中查找
        value = self.variables
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
```

### 流程识别器

```python
# backend/workflow/workflow_identifier.py
from typing import Optional, Dict, Any
from backend.services.llm_service import LLMService

class WorkflowIdentifier:
    """流程识别器，决定使用 SOP 还是动态编排"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.workflow_registry = {
            "pdf_analysis": "pdf_analysis_sop.yaml",
            "code_review": "code_review_sop.yaml",
            "document_generation": "document_generation_sop.yaml",
            # ... 其他 SOP
        }
    
    async def identify(
        self, 
        task: str
    ) -> Dict[str, Any]:
        """
        识别任务类型，决定执行模式
        
        Returns:
            {
                "mode": "sop" | "dynamic",
                "workflow_name": "workflow_name" (如果 mode=sop),
                "confidence": 0.0-1.0
            }
        """
        # 使用 LLM 分析任务
        analysis = await self.llm_service.chat(
            f"""分析以下任务，判断是否有匹配的标准流程（SOP）：
            
可用流程：
{chr(10).join(f"- {name}: {desc}" for name, desc in self.get_workflow_descriptions().items())}

任务：{task}

如果有匹配的流程，返回流程名称；否则返回 "dynamic"。
只返回流程名称或 "dynamic"，不要其他内容。"""
        )
        
        workflow_name = analysis.strip().lower()
        
        if workflow_name in self.workflow_registry:
            return {
                "mode": "sop",
                "workflow_name": workflow_name,
                "confidence": 0.9
            }
        else:
            return {
                "mode": "dynamic",
                "workflow_name": None,
                "confidence": 0.5
            }
    
    def get_workflow_descriptions(self) -> Dict[str, str]:
        """获取所有流程的描述"""
        return {
            "pdf_analysis": "PDF文档分析和总结",
            "code_review": "代码审查和优化建议",
            "document_generation": "文档生成",
        }
```

### 集成到 Orchestrator

```python
# backend/agent/orchestrator.py (更新)
from backend.workflow.workflow_engine import WorkflowEngine
from backend.workflow.workflow_identifier import WorkflowIdentifier

class Orchestrator:
    def __init__(self):
        # ... 现有代码
        self.workflow_engine = WorkflowEngine(self)
        self.workflow_identifier = WorkflowIdentifier()
    
    async def process(self, task: str, context: Optional[Dict] = None) -> str:
        """处理任务，支持 SOP 和动态编排"""
        # 1. 识别任务类型
        identification = await self.workflow_identifier.identify(task)
        
        if identification["mode"] == "sop":
            # 2a. 执行 SOP 流程
            workflow_name = identification["workflow_name"]
            input_data = {
                "task": task,
                "context": context or {}
            }
            result = await self.workflow_engine.execute_workflow(
                workflow_name,
                input_data
            )
            return result
        else:
            # 2b. 动态编排执行
            return await self.process_dynamic(task, context)
```

### 目录结构更新

```
backend/
├── workflow/                  # SOP 流程编排
│   ├── __init__.py
│   ├── workflow_engine.py     # 流程执行引擎
│   ├── workflow_identifier.py # 流程识别器
│   ├── workflow_state.py      # 流程状态管理
│   └── validators.py          # 流程验证器
│
├── workflows/                 # SOP 流程定义文件
│   ├── pdf_analysis_sop.yaml
│   ├── code_review_sop.yaml
│   └── document_generation_sop.yaml
│
└── agent/
    └── orchestrator.py        # 集成流程编排
```

### SOP vs 动态编排

| 特性 | SOP 流程编排 | 动态编排 (Orchestrator) |
|------|-------------|----------------------|
| **适用场景** | 标准化、重复性任务 | 创新性、复杂任务 |
| **执行方式** | 预定义流程 | LLM 动态分析 |
| **一致性** | 高（固定流程） | 中（可能变化） |
| **灵活性** | 低（需修改定义） | 高（自动适应） |
| **执行速度** | 快（无需分析） | 慢（需要分析） |
| **质量控制** | 高（流程保证） | 中（依赖 LLM） |

### SOP 使用示例

```python
# 用户请求："分析这个PDF文件"
# 系统识别为 pdf_analysis SOP，执行标准流程

result = await orchestrator.process("分析 document.pdf")

# 执行流程：
# 1. 文档加载 (PDF Agent)
# 2. 文本提取 (PDF Agent)
# 3. 内容分析 (Chat Agent)
# 4. 生成摘要 (Chat Agent)
# 5. 结果验证 (Chat Agent)
# 返回标准化的分析结果
```

## 总结

对于类似 Cursor Agent 的复杂 CLI 工具，**前后端分离架构 + 多 Agent 协作 + SOP 流程编排**是完整的解决方案：

- ✅ **前端进程**：负责 Rich UI 渲染和用户交互
- ✅ **后端进程**：负责 Agent 逻辑、LLM 调用、工具执行
- ✅ **多 Agent 协作**：通过 Orchestrator 和 Coordinator 协调多个专门化的 Agent
- ✅ **SOP 流程编排**：支持标准化流程和动态编排两种模式
- ✅ **进程间通信**：通过 IPC (TCP Localhost) 通信
- ✅ **独立运行**：两个进程可以独立启动、重启、扩展

这种架构提供了：
- 更好的稳定性、可扩展性和用户体验
- 处理复杂任务的能力（通过多 Agent 协作）
- 灵活的 Agent 组合和扩展
- 标准化流程执行（通过 SOP）
- 智能的任务识别和执行模式选择
