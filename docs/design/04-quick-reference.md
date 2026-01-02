# 快速参考指南

## CLI Agent 架构决策快速参考

### 核心问题：类似 Cursor Agent 的 CLI 需要前后端分离吗？

**答案：需要！前后端应该分离，运行在不同进程中**

### 为什么需要前后端分离？

1. **进程隔离**
   - 前端 UI 进程和后端 Agent 进程分离
   - 后端崩溃不影响前端 UI
   - 前端可以独立重启

2. **可扩展性**
   - 后端可以独立扩展（多进程、多线程）
   - 支持多个前端客户端
   - 可以添加其他类型的客户端

3. **资源管理**
   - 后端统一管理 LLM 连接
   - 统一管理工具执行
   - 更好的资源利用

4. **稳定性**
   - 错误隔离
   - 独立故障恢复
   - 更好的容错能力

### 架构概览

```
前端进程 (Rich UI)
    ↓ IPC (TCP Localhost)
后端进程 (Agent Service)
    ↓
LLM API / 工具执行
```

**关键点**：
- ✅ 两个独立的进程
- ✅ 通过 IPC (TCP Localhost) 通信
- ✅ 前端负责 UI，后端负责业务逻辑

### 通信方式：IPC (TCP Localhost)

**已选择**：使用 IPC (TCP Localhost) 作为通信方式

**优点**：
- ✅ 跨平台兼容（Windows、Mac、Linux）
- ✅ 实现简单，易于维护
- ✅ 支持流式输出
- ✅ 打包后稳定可靠

### 目录结构

```
hou-cli/
├── frontend/          # 前端进程（CLI 用户界面）
│   ├── main.py       # CLI 入口
│   ├── ui/           # Rich UI 组件
│   └── client/       # IPC 客户端
├── backend/          # 后端进程（Agent 服务）
│   ├── main.py       # 后端服务入口
│   ├── api/         # API 路由
│   ├── agent/       # Agent 核心
│   └── services/    # 服务层
├── cli.py            # 统一启动脚本（可选）
└── shared/          # 共享代码
```

### CLI 入口说明

- **`frontend/main.py`**：CLI 主入口（前端即 CLI）
  - 包含 Rich UI 和用户交互
  - 通过 IPC 与后端通信
  - 用户直接运行的就是这个文件

- **`backend/main.py`**：后端服务入口
  - 启动 IPC 服务器
  - 运行 Agent 服务

- **`cli.py`**：统一启动脚本（可选）
  - 用于生产模式，同时启动前后端

### UI 设计风格（参考 Cursor Agent）

**核心原则**：
- ✅ **简洁优先**：不使用过多的装饰元素，直接显示内容
- ✅ **一致性**：统一的提示符风格（`▸` 或 `>`）
- ✅ **清晰性**：用户输入和 Agent 回复有明显的视觉区分
- ✅ **专业性**：不显示技术细节（如会话 ID）

**示例**：
```
▸ 你好
你好！我是你的 AI 助手。

▸ 帮我写一个 Python 函数
```python
def hello():
    print("Hello, World!")
```
```

**Panel 使用**：
- ✅ 错误提示（特殊场景）
- ✅ 状态显示（特殊场景）
- ❌ 普通对话回复（不使用 Panel）

**流式输出**：
- ✅ 使用 Rich Live 组件实时更新
- ✅ 避免重复显示
- ✅ 支持 Markdown 和代码块实时渲染

详细说明请参考：[04-rich-ui-guide.md](./04-rich-ui-guide.md)

### 启动方式

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

### 与单进程 CLI 的区别

| 特性 | 单进程 CLI | 前后端分离 CLI |
|------|-----------|--------------|
| 进程数 | 1 个 | 2 个（前端+后端） |
| 通信方式 | 函数调用 | IPC (TCP Localhost) |
| 稳定性 | 低（一处崩溃全崩溃） | 高（进程隔离） |
| 可扩展性 | 低 | 高（支持多客户端） |
| 复杂度 | 低 | 中 |

### 多 Agent 协作

对于复杂任务，系统支持多 Agent 协作：

```
用户请求
    ↓
Orchestrator (编排器)
    ├── 任务分解
    ├── Agent 选择
    └── 结果聚合
    ↓
多个专门化 Agent
├── Chat Agent (对话)
├── PDF Agent (文档处理)
├── Code Agent (代码生成)
└── Research Agent (研究)
```

**执行模式**：
- **顺序执行**：Agent1 → Agent2 → Agent3
- **并行执行**：同时执行多个独立任务
- **流水线执行**：前一个的输出作为后一个的输入

详细说明请参考：[01-multi-agent-design.md](./01-multi-agent-design.md)

### 下一步行动

1. ✅ 创建 `backend/` 目录和 API 服务器
2. ✅ 创建 `frontend/` 目录和 Rich UI
3. ✅ 实现 IPC 通信层（TCP Localhost）
4. ✅ 实现多 Agent 协作架构（Orchestrator + Coordinator）
5. ✅ 实现专门化 Agent（PDF、Code、Chat 等）
6. ✅ 迁移现有功能到后端服务
7. ✅ 实现前端 UI 组件

### SOP 流程编排

对于需要标准化执行的任务，系统支持 SOP (标准操作流程)：

```
用户请求
    ↓
流程识别器
    ├── 匹配 SOP 模板 → SOP 流程执行
    └── 无匹配 → 动态编排执行
    ↓
流程执行引擎
    ├── 加载流程定义
    ├── 执行步骤（顺序/并行/循环）
    ├── 条件分支处理
    └── 错误处理和重试
```

**SOP vs 动态编排**：
- **SOP**：标准化、重复性任务，预定义流程
- **动态编排**：创新性、复杂任务，LLM 动态分析

详细说明请参考：[01-sop-workflow-design.md](./01-sop-workflow-design.md)

### 完整架构

```
前端 (Rich UI)
    ↓
后端 (Agent Service)
    ├── 流程识别器
    ├── SOP 流程引擎 (标准化流程)
    ├── Orchestrator (动态编排)
    ├── Coordinator (Agent协调)
    └── 多个专门化 Agent
```

### IPC 通信和打包

**通信方式**：IPC（进程间通信）- TCP Localhost

**跨平台支持**：
- ✅ Windows
- ✅ macOS
- ✅ Linux

**打包方案**：
- PyInstaller（跨平台打包）
- Windows: Inno Setup（安装程序）
- macOS: DMG（磁盘镜像）
- Linux: AppImage（便携应用）

详细说明请参考：[02-ipc-and-packaging.md](./02-ipc-and-packaging.md)

### 完整架构

```
前端 (Rich UI) ←→ IPC (TCP Localhost) ←→ 后端 (Agent Service)
    ├── 流程识别器
    ├── SOP 流程引擎 (标准化流程)
    ├── Orchestrator (动态编排)
    ├── Coordinator (Agent协调)
    └── 多个专门化 Agent
```

### 知识库管理

**核心功能**：
- ✅ 临时文件存储区域
- ✅ 知识提炼存档区域
- ✅ 知识入库（向量化）
- ✅ 向量搜索能力

**工作流程**：
```
文件上传 → 临时存储 → 知识提炼 → 归档存储 → 向量化 → 向量数据库 → 搜索服务
```

详细说明请参考：[01-knowledge-base-design.md](./01-knowledge-base-design.md)

### 代码能力和长记忆

**核心功能**：
- ✅ 代码读取和分析能力
- ✅ 代码编辑和重构能力
- ✅ 文件系统结构读取
- ✅ 长记忆存储和检索
- ✅ 上下文管理和整理

**代码能力**：
- 读取代码文件（支持多种语言）
- 分析代码结构（函数、类、导入等）
- 编辑代码（替换、插入、删除、重构）
- 生成代码差异

**长记忆系统**：
- 代码快照存储
- 编辑历史记录
- 项目结构记忆
- 向量化搜索

**上下文管理**：
- 会话上下文整理
- 代码上下文缓存
- 上下文压缩和摘要
- 相关上下文检索

详细说明请参考：[01-code-and-memory-design.md](./01-code-and-memory-design.md)

### 代码执行和安全

**核心功能**：
- ✅ 代码执行能力（Python、Shell 等）
- ✅ 沙箱隔离执行环境
- ✅ 权限控制和命令过滤
- ✅ 资源限制（CPU、内存、时间）
- ✅ 执行审计日志

**安全机制**：
- 多层防护：权限检查 + 命令过滤 + 沙箱隔离
- 白名单/黑名单：控制可执行的命令
- 资源限制：防止资源滥用
- 审计日志：记录所有执行操作
- 沙箱隔离：在隔离环境中执行

详细说明请参考：[01-code-execution-and-security.md](./01-code-execution-and-security.md)

### 完整架构

```
前端 (Rich UI) ←→ IPC (TCP Localhost) ←→ 后端 (Agent Service)
    ├── 流程识别器
    ├── SOP 流程引擎 (标准化流程)
    ├── Orchestrator (动态编排)
    ├── Coordinator (Agent协调)
    ├── 多个专门化 Agent
    └── 知识库管理
        ├── 文件存储管理
        ├── 知识提炼处理
        ├── 向量存储服务
        └── 向量搜索服务
```

详细说明请参考：
- [00-architecture-design.md](./00-architecture-design.md) - 整体架构设计
- [01-multi-agent-design.md](./01-multi-agent-design.md) - 多 Agent 协作设计
- [01-sop-workflow-design.md](./01-sop-workflow-design.md) - SOP 流程编排设计
- [02-ipc-and-packaging.md](./02-ipc-and-packaging.md) - IPC 通信和打包方案
- [01-knowledge-base-design.md](./01-knowledge-base-design.md) - 知识库管理设计
- [01-code-and-memory-design.md](./01-code-and-memory-design.md) - 代码能力和长记忆设计
- [01-code-execution-and-security.md](./01-code-execution-and-security.md) - 代码执行和安全设计
