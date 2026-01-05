# Backend 模块说明

## 目录结构

```
backend/
├── api/                    # 接口层（只负责 HTTP 接口）
│   ├── routes.py           # 路由定义
│   └── handlers.py         # 请求处理（可选）
│
├── core/                    # 核心业务逻辑层
│   ├── agent/              # Agent 相关
│   │   ├── orchestrator.py # Agent 编排器
│   │   ├── coordinator.py  # Agent 协调器
│   │   ├── base_agent.py   # Agent 基类
│   │   └── agents/         # 具体 Agent 实现
│   │       ├── chat_agent.py
│   │       ├── code_agent.py
│   │       ├── pdf_agent.py
│   │       └── filesystem_agent.py
│   └── workflow/           # 工作流
│       ├── workflow_engine.py
│       ├── workflow_identifier.py
│       └── workflow_state.py
│
├── services/                # 服务层
│   ├── llm/                # LLM 服务
│   │   └── llm_service.py
│   └── tools/               # 工具服务
│       └── tool_service.py
│
└── infrastructure/          # 基础设施层
    ├── execution/          # 代码执行
    ├── knowledge/          # 知识库
    ├── memory/            # 记忆管理
    └── security/           # 安全
```

## 分层架构

### 1. API 层（api/）
- **职责**：处理 HTTP 请求，参数验证，响应格式化
- **依赖**：只依赖 `core` 层
- **不包含**：业务逻辑

### 2. Core 层（core/）
- **职责**：核心业务逻辑，Agent 编排，工作流执行
- **依赖**：`services` 层和 `infrastructure` 层
- **包含**：
  - `agent/` - Agent 相关业务逻辑
  - `workflow/` - 工作流相关业务逻辑

### 3. Services 层（services/）
- **职责**：外部服务封装（LLM、工具等）
- **依赖**：`infrastructure` 层
- **包含**：
  - `llm/` - LLM 服务封装
  - `tools/` - 工具服务封装

### 4. Infrastructure 层（infrastructure/）
- **职责**：基础设施功能（执行、存储、安全等）
- **依赖**：无（最底层）
- **包含**：
  - `execution/` - 代码执行
  - `knowledge/` - 知识库管理
  - `memory/` - 记忆管理
  - `security/` - 安全相关

## 导入规则

### ✅ 正确的导入方式

```python
# API 层导入 Core 层
from backend.core.agent.orchestrator import Orchestrator

# Core 层导入 Services 层
from backend.services.llm.llm_service import LLMService

# Core 层导入 Infrastructure 层
from backend.infrastructure.memory.context_manager import ContextManager

# Services 层导入 Infrastructure 层
from backend.infrastructure.security.sandbox import Sandbox
```

### ❌ 错误的导入方式

```python
# API 层不应该直接导入 Services 或 Infrastructure
from backend.services.llm.llm_service import LLMService  # ❌

# 同层之间不应该相互导入（除非必要）
from backend.core.workflow.workflow_engine import WorkflowEngine  # ⚠️ 谨慎使用
```

## 依赖关系

```
api/
  └─> core/
        ├─> services/
        │     └─> infrastructure/
        └─> infrastructure/
```

## 模块职责

### API 层
- 接收 HTTP 请求
- 参数验证和序列化
- 调用 Core 层处理业务逻辑
- 格式化响应

### Core 层
- Agent 编排和协调
- 工作流执行
- 业务逻辑处理

### Services 层
- LLM API 调用封装
- 工具服务封装
- 外部服务集成

### Infrastructure 层
- 代码执行引擎
- 知识库存储和检索
- 记忆管理
- 安全机制








