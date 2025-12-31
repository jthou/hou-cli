# Hou CLI - LLM Agent CLI Tool

一个功能强大的 LLM Agent 命令行工具，支持多 Agent 协作、知识库管理、代码执行等功能。

## 特性

- 🖥️ **Rich UI**：美观的终端界面
- 🤖 **多 Agent 协作**：支持多个专门化 Agent 协同工作
- 📋 **SOP 流程编排**：标准化工作流程执行
- 📚 **知识库管理**：文件存储、知识提炼、向量搜索
- 💻 **代码能力**：代码读取、编辑、执行
- 🔒 **安全执行**：沙箱隔离、权限控制、资源限制

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- 推荐 Python 3.11 或 3.12

### 安装

1. **克隆项目**
```bash
git clone <repository-url>
cd hou-cli
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **安装开发依赖（可选）**
```bash
pip install -r requirements-dev.txt
```

### 运行

**🎯 最简单的方式（推荐）**：

**一键启动前后端：**
```bash
# macOS/Linux
./start-all.sh

# Windows
start-all.bat

# 或使用 Make
make run
```

**分别启动（开发用）：**
```bash
# 启动后端（后台）
./start.sh          # macOS/Linux
start.bat           # Windows
make start          # 使用 Make

# 启动前端（新终端）
./start-frontend.sh # macOS/Linux
start-frontend.bat  # Windows
make run-frontend   # 使用 Make
```

**所有脚本都会自动激活虚拟环境，无需手动执行 `source venv/bin/activate`！**

## 配置

创建 `.env` 文件：

```bash
DEEPSEEK_API_KEY=your_api_key_here
OLLAMA_MODEL=deepseek-r1:14b
LOG_LEVEL=INFO
```

## 项目结构

```
hou-cli/
├── frontend/          # 前端进程（CLI 用户界面）
├── backend/           # 后端进程（Agent 服务）
├── shared/            # 共享代码
├── workflows/         # SOP 流程定义
├── docs/              # 文档
│   └── design/        # 设计文档
└── archived/          # 归档代码
```

## 文档

详细文档请查看 [docs/design/](./docs/design/) 目录：

- [架构设计](./docs/design/architecture-design.md)
- [快速参考](./docs/design/quick-reference.md)
- [依赖管理](./docs/design/dependency-management.md)
- [多 Agent 协作](./docs/design/multi-agent-design.md)
- [SOP 流程编排](./docs/design/sop-workflow-design.md)
- [知识库管理](./docs/design/knowledge-base-design.md)
- [代码执行和安全](./docs/design/code-execution-and-security.md)

## 开发

### 代码格式化

```bash
black .
isort .
```

### 代码检查

```bash
flake8 .
mypy .
```

### 运行测试

```bash
pytest
```

## 许可证

MIT License

