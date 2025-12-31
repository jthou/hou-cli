# 🚀 快速启动指南

## 🎯 最简单的方式（推荐）

### 方式 1: 一键启动前后端（最推荐）

**macOS/Linux:**
```bash
./start-all.sh
```

**Windows:**
```cmd
start-all.bat
```

**或使用 Make:**
```bash
make run
```

这会：
- ✅ 自动激活虚拟环境
- ✅ 后台启动后端服务
- ✅ 启动前端 CLI（交互式）

### 方式 2: 分别启动（推荐用于开发）

**步骤 1: 启动后端（后台）**

**macOS/Linux:**
```bash
./start.sh
```

**Windows:**
```cmd
start.bat
```

**或使用 Make:**
```bash
make start
```

**步骤 2: 启动前端（新终端）**

**macOS/Linux:**
```bash
./start-frontend.sh
```

**Windows:**
```cmd
start-frontend.bat
```

**或使用 Make:**
```bash
make run-frontend
```

## 📋 所有启动方式

### 使用脚本（最简单，自动激活虚拟环境）

| 操作 | macOS/Linux | Windows | 说明 |
|------|------------|---------|------|
| 启动后端 | `./start.sh` | `start.bat` | 后台运行 |
| 启动前端 | `./start-frontend.sh` | `start-frontend.bat` | 交互式 |
| 启动全部 | `./start-all.sh` | `start-all.bat` | 后端后台+前端交互 |
| 停止后端 | `./stop.sh` | `stop.bat` | 停止后台服务 |

### 使用 Make（推荐）

```bash
make start          # 启动后端（后台）
make run-frontend   # 启动前端
make run            # 启动全部（后端后台+前端交互）
make stop-backend   # 停止后端
make status-backend  # 查看后端状态
make restart-backend # 重启后端
```

### 使用 Python 直接运行

```bash
# 需要先激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 然后运行
python cli.py start       # 启动后端（后台）
python cli.py stop        # 停止后端
python cli.py status      # 查看状态
python cli.py restart     # 重启后端
python -m frontend.main chat  # 启动前端
```

## 🎯 推荐工作流程

### 日常使用（最简单）

```bash
# 一键启动前后端
./start-all.sh
# 或 make run
```

### 开发调试（推荐）

```bash
# 终端 1: 启动后端（后台）
./start.sh
# 或 make start

# 终端 2: 启动前端
./start-frontend.sh
# 或 make run-frontend
```

### 调试后端（前台运行）

```bash
# 终端 1: 启动后端（前台，可看日志）
source venv/bin/activate
python cli.py start --foreground
# 或 make run-backend

# 终端 2: 启动前端
./start-frontend.sh
```

## 💡 管理后端服务

### 查看后端状态
```bash
make status-backend
# 或
./stop.sh  # 会显示状态
```

### 停止后端服务
```bash
make stop-backend
# 或
./stop.sh
```

### 重启后端服务
```bash
make restart-backend
```

## ✅ 优势

- ✅ **无需手动激活虚拟环境** - 所有脚本自动处理
- ✅ **统一启动方式** - 前后端使用相同的脚本模式
- ✅ **简单易记** - `./start.sh` 和 `./start-frontend.sh`
- ✅ **跨平台支持** - macOS/Linux/Windows 都有对应脚本
- ✅ **后台运行** - 后端不占据终端

## 📝 常见问题

**Q: 为什么不需要 `source venv/bin/activate`？**  
A: 所有启动脚本（`start.sh`, `start-frontend.sh` 等）都会自动激活虚拟环境

**Q: 如何查看后端日志？**  
A: 使用前台模式：`python cli.py start --foreground` 或 `make run-backend`

**Q: 后端启动失败怎么办？**  
A: 检查虚拟环境是否存在，运行 `python -m venv venv` 创建

**Q: 如何确认后端在运行？**  
A: 运行 `make status-backend` 或 `python cli.py status`
