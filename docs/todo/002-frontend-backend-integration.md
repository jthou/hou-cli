# TODO-002: 前后端对话集成

## 任务概述

完成前后端的完整集成，确保前端可以正常与后端通信，实现端到端的对话功能。

**优先级**: 高  
**预计工时**: 1-2 天  
**状态**: 进行中

---

## 一、集成检查清单

### 1.1 后端服务检查
- [x] 后端主程序 (`backend/main.py`) 存在
- [x] API 路由 (`backend/api/routes.py`) 存在
- [x] Orchestrator (`backend/core/agent/orchestrator.py`) 存在
- [x] LLM Service (`backend/services/llm/llm_service.py`) 存在
- [x] `.env` 文件加载支持

### 1.2 前端服务检查
- [x] 前端主程序 (`frontend/main.py`) 存在
- [x] IPC 客户端 (`frontend/client/ipc_client.py`) 存在
- [x] Rich UI 组件存在
- [x] `.env` 文件加载支持

### 1.3 通信机制检查
- [x] IPC (TCP Localhost) 实现
- [x] 端口文件管理 (`shared/platform_utils.py`)
- [x] 健康检查接口 (`/health`)
- [x] 非流式接口 (`/api/chat`)
- [x] 流式接口 (`/api/chat/stream`)

---

## 二、集成测试步骤

### 2.1 启动后端服务

```bash
# 方法 1: 直接启动
python -m backend.main

# 方法 2: 使用 cli.py
python cli.py start

# 方法 3: 使用 Makefile
make start
```

**验证**:
- [ ] 后端服务成功启动
- [ ] 端口文件已创建
- [ ] 健康检查接口可访问 (`http://127.0.0.1:{port}/health`)

### 2.2 启动前端服务

```bash
# 方法 1: 单次对话
python -m frontend.main chat "你好"

# 方法 2: 交互式对话
python -m frontend.main chat

# 方法 3: 非流式响应
python -m frontend.main chat "你好" --no-stream
```

**验证**:
- [ ] 前端成功连接到后端
- [ ] 可以发送消息
- [ ] 可以接收响应（流式和非流式）

### 2.3 端到端测试场景

#### 场景 1: 简单问答（非流式）
```bash
python -m frontend.main chat "你好，你是谁？" --no-stream
```

**预期结果**:
- 前端显示完整的回复
- 回复内容合理

#### 场景 2: 简单问答（流式）
```bash
python -m frontend.main chat "你好，你是谁？"
```

**预期结果**:
- 前端实时显示流式输出
- 输出流畅无卡顿

#### 场景 3: 交互式对话
```bash
python -m frontend.main chat
```

**预期结果**:
- 可以连续进行多轮对话
- 每轮对话都能正常响应

#### 场景 4: 错误处理
```bash
# 后端未启动时
python -m frontend.main chat "测试"
```

**预期结果**:
- 显示友好的错误提示
- 提示用户启动后端服务

---

## 三、已知问题和解决方案

### 问题 1: 后端启动时 Orchestrator 初始化需要 API Key

**原因**: `backend/api/routes.py` 在模块级别创建 `Orchestrator()` 实例，而 `Orchestrator` 会创建 `LLMService`，需要 API Key。

**解决方案**:
- ✅ 已在 `backend/main.py` 和 `frontend/main.py` 中添加 `.env` 文件加载
- ✅ 测试文件已设置默认测试 API Key

### 问题 2: 端口文件读取超时

**原因**: 前端启动时后端可能还未完全启动。

**解决方案**:
- ✅ IPC 客户端已有重试机制（最多 5 次，间隔 1 秒）
- ✅ 健康检查确保后端就绪

---

## 四、验收标准

- [ ] 后端服务可以正常启动
- [ ] 前端可以成功连接到后端
- [ ] 非流式对话功能正常
- [ ] 流式对话功能正常
- [ ] 交互式对话功能正常
- [ ] 错误处理友好且明确
- [ ] 多轮对话上下文正常（如果已实现）

---

## 五、相关文件

### 后端文件
- `backend/main.py` - 后端主程序
- `backend/api/routes.py` - API 路由定义
- `backend/core/agent/orchestrator.py` - Agent 编排器
- `backend/services/llm/llm_service.py` - LLM 服务

### 前端文件
- `frontend/main.py` - 前端主程序
- `frontend/client/ipc_client.py` - IPC 客户端
- `frontend/ui/banner.py` - 启动画面
- `frontend/ui/panels.py` - UI 面板组件

### 共享文件
- `shared/platform_utils.py` - 平台工具（端口管理）
- `cli.py` - 统一启动脚本
- `env.example` - 环境变量模板

---

## 六、测试脚本

使用 `test_integration.py` 进行快速检查：

```bash
python tests/test_integration.py
```

---

**创建时间**: 2025-12-31  
**最后更新**: 2025-12-31

