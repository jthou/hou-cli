# 后端模块重构计划

## 当前问题

1. **api 和 agent 在同一层级** - 接口层和业务逻辑层混在一起
2. **services 中的 tool_service 和其他工具分散** - 工具相关代码不统一
3. **缺乏清晰的分层架构** - 各模块职责不明确

## 目标结构

```
backend/
├── api/                    # 接口层（只负责 HTTP 接口）
│   ├── routes.py           # 路由定义
│   └── handlers.py         # 请求处理
│
├── core/                    # 核心业务逻辑层
│   ├── agent/              # Agent 相关
│   │   ├── orchestrator.py
│   │   ├── coordinator.py
│   │   ├── base_agent.py
│   │   └── agents/         # 具体 Agent 实现
│   └── workflow/           # 工作流
│       ├── workflow_engine.py
│       └── workflow_identifier.py
│
├── services/                # 服务层
│   ├── llm/                # LLM 服务
│   │   └── llm_service.py
│   └── tools/              # 工具服务
│       └── tool_service.py
│
└── infrastructure/          # 基础设施层
    ├── execution/          # 代码执行
    ├── knowledge/          # 知识库
    ├── memory/            # 记忆管理
    └── security/           # 安全
```

## 分层说明

### 1. API 层（api/）
- **职责**：处理 HTTP 请求，参数验证，响应格式化
- **依赖**：只依赖 core 层
- **不包含**：业务逻辑

### 2. Core 层（core/）
- **职责**：核心业务逻辑，Agent 编排，工作流执行
- **依赖**：services 层和 infrastructure 层
- **包含**：agent/, workflow/

### 3. Services 层（services/）
- **职责**：外部服务封装（LLM、工具等）
- **依赖**：infrastructure 层
- **包含**：llm/, tools/

### 4. Infrastructure 层（infrastructure/）
- **职责**：基础设施功能（执行、存储、安全等）
- **依赖**：无（最底层）
- **包含**：execution/, knowledge/, memory/, security/

## 迁移步骤

1. 创建新目录结构
2. 移动文件到对应目录
3. 更新所有导入路径
4. 更新文档
5. 运行测试确保功能正常








