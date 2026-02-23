# Web 前端服务使用指南

## 概述

Web 前端服务提供了基于浏览器的用户界面，与现有的 CLI 前端并行运行。

## 功能特性

- ✅ **Web 界面**：基于浏览器的现代化 UI
- ✅ **实时聊天**：支持流式响应（SSE）
- ✅ **会话管理**：自动管理会话 ID
- ✅ **状态监控**：显示后端连接状态
- ✅ **响应式设计**：支持桌面和移动设备

## 快速开始

### 启动方式

#### 方式 1: 使用 Makefile（推荐）

```bash
# 启动后端 + Web 前端
make start-web

# 或分别启动
make run-backend    # 启动后端
make run-web        # 启动 Web 前端
```

#### 方式 2: 手动启动

```bash
# 1. 启动后端
python cli.py start

# 2. 启动 Web 前端
python -m backend.main
```

#### 方式 3: 使用 Python 模块

```bash
# 在虚拟环境中
source venv/bin/activate
python -m backend.main
```

### 访问 Web 界面

启动后，在浏览器中访问：
```
http://127.0.0.1:8080
```

默认端口是 8080，如果被占用会自动查找可用端口。

## 配置

### 环境变量

```bash
# .env 文件
WEB_PORT=8080              # Web 前端端口（默认 8080）
BACKEND_PORT=8000           # 后端服务端口（默认自动发现）
```

### 端口配置

- **Web 前端端口**：通过 `WEB_PORT` 环境变量配置，默认 8080
- **后端端口**：自动从端口文件或环境变量读取

## 架构

```
┌─────────────────────────────────────────┐
│         浏览器 (Browser)                 │
│  http://127.0.0.1:8080                  │
└─────────────────────────────────────────┘
                  │
                  │ HTTP/WebSocket
                  ▼
┌─────────────────────────────────────────┐
│      Web 前端服务 (FastAPI)              │
│  - 静态文件服务                          │
│  - WebSocket 代理                        │
│  - API 代理                              │
└─────────────────────────────────────────┘
                  │
                  │ HTTP (localhost)
                  ▼
┌─────────────────────────────────────────┐
│      后端服务 (FastAPI)                  │
│  - LLM Agent 服务                        │
│  - 工具和技能管理                         │
└─────────────────────────────────────────┘
```

## API 端点

### Web 前端端点

- `GET /` - Web 界面主页
- `GET /api/backend-url` - 获取后端服务 URL
- `POST /api/chat` - 非流式聊天（代理到后端）
- `WebSocket /ws` - WebSocket 连接（用于流式聊天）

### 后端端点（通过代理）

所有后端 API 都可以通过 Web 前端访问，Web 前端作为代理转发请求。

## 使用说明

### 基本使用

1. **启动服务**
   ```bash
   make start-web
   ```

2. **打开浏览器**
   - 访问 `http://127.0.0.1:8080`
   - 等待后端连接状态显示"已连接"

3. **开始聊天**
   - 在输入框中输入消息
   - 按 Enter 发送（Shift+Enter 换行）
   - 或点击"发送"按钮

### 功能说明

- **流式响应**：消息会实时流式显示
- **会话管理**：自动管理会话 ID，保持上下文
- **状态监控**：顶部显示后端连接状态
- **错误处理**：连接错误时会显示友好提示

## 与 CLI 前端的区别

| 特性 | CLI 前端 | Web 前端 |
|------|---------|---------|
| **界面** | 终端（Rich UI） | 浏览器 |
| **启动** | `make start` | `make start-web` |
| **访问** | 终端命令 | 浏览器 URL |
| **流式响应** | ✅ 支持 | ✅ 支持 |
| **会话管理** | ✅ 支持 | ✅ 支持 |
| **适用场景** | 命令行用户 | Web 用户 |

## 开发

### 文件结构

```
frontend/web/
├── __init__.py
├── main.py              # Web 服务主文件
├── templates/           # HTML 模板
│   └── index.html
└── static/              # 静态文件
    ├── style.css        # 样式文件
    └── app.js           # 前端 JavaScript
```

### 修改样式

编辑 `frontend/web/static/style.css` 文件。

### 修改前端逻辑

编辑 `frontend/web/static/app.js` 文件。

### 修改模板

编辑 `frontend/web/templates/index.html` 文件。

## 故障排查

### 1. Web 前端无法启动

**检查**：
- 端口是否被占用
- 虚拟环境是否激活
- 依赖是否安装（`jinja2`）

**解决**：
```bash
# 检查端口
lsof -i :8080

# 重新安装依赖
pip install -r requirements.txt
```

### 2. 无法连接到后端

**检查**：
- 后端服务是否运行
- 后端端口是否正确
- 浏览器控制台错误信息

**解决**：
```bash
# 检查后端状态
make status

# 检查后端端口
cat ~/.local/share/hou-cli/port.txt  # Linux/macOS
```

### 3. WebSocket 连接失败

**检查**：
- 浏览器是否支持 WebSocket
- 防火墙设置
- 后端服务是否正常

**解决**：
- 使用现代浏览器（Chrome、Firefox、Safari、Edge）
- 检查浏览器控制台错误

## 总结

Web 前端服务提供了：
- ✅ 现代化的浏览器界面
- ✅ 与 CLI 前端并行运行
- ✅ 完整的聊天功能
- ✅ 流式响应支持
- ✅ 易于扩展和定制

现在你可以选择使用 CLI 或 Web 界面来使用 Hou CLI！
