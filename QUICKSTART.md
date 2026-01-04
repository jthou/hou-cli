# 快速开始指南

## ✅ 项目已设置完成

所有依赖已安装，项目结构已创建。

## 启动项目

### 🎯 最简单的方式（推荐）

```bash
# macOS/Linux
./start.sh

# Windows
start.bat

# 或使用 Make
make start
```

**就这么简单！** 脚本会自动激活虚拟环境并启动服务。

### 其他方式

#### 方式 1：使用 Python 直接运行
```bash
python cli.py
```

#### 方式 2：分别启动（开发调试用）

**终端 1 - 启动后端**：
```bash
source venv/bin/activate
python -m backend.main
```

**终端 2 - 启动前端**：
```bash
source venv/bin/activate
python -m frontend.main chat
```

#### 方式 3：使用 Makefile

```bash
# 一键启动（推荐）
make start

# 或分别启动
make run-backend  # 终端 1
make run-frontend # 终端 2
```

## 配置环境变量

创建 `.env` 文件（可选）：

```bash
DEEPSEEK_API_KEY=your_api_key_here
OLLAMA_MODEL=deepseek-r1:14b
LOG_LEVEL=INFO
```

## 验证安装

```bash
source venv/bin/activate

# 检查模块导入
python -c "import backend; import frontend; import shared; print('✅ 安装成功！')"

# 查看 CLI 帮助
python -m frontend.main --help
```

## 下一步

1. **配置 LLM API Key**：在 `.env` 文件中设置 `DEEPSEEK_API_KEY`
2. **启动后端服务**：`python -m backend.main`
3. **启动前端 CLI**：`python -m frontend.main chat`
4. **开始开发**：查看 `docs/design/` 目录了解架构设计

## 常用命令

```bash
# 格式化代码
make format

# 代码检查
make lint

# 运行测试
make test

# 查看所有命令
make help
```

## 项目状态

- ✅ 虚拟环境已创建
- ✅ 所有依赖已安装
- ✅ 项目结构已创建
- ✅ 基本模块可正常导入
- ⚠️ 部分功能待实现（标记为 TODO）

## 注意事项

1. **首次运行前端前，必须先启动后端**
2. **LLM API Key** 需要配置才能使用 LLM 功能
3. **部分功能还在开发中**，代码中有 TODO 标记

