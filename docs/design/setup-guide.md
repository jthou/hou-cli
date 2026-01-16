# 项目设置指南

## 使用 pyproject.toml（推荐）

本项目使用 `pyproject.toml` 作为主要的依赖管理方式，这是现代 Python 项目的标准做法。

## 快速开始

### 1. 环境准备

确保已安装 Python 3.10 或更高版本（推荐 3.11）：

```bash
python --version
# 应该显示 Python 3.10+ 或 3.11+
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. 安装项目

**安装生产依赖**：
```bash
pip install -e .
```

**安装开发依赖**（推荐）：
```bash
pip install -e ".[dev]"
```

这将安装：
- 所有生产依赖
- 开发工具（pytest, black, mypy 等）
- 项目本身（可编辑模式）

### 4. 验证安装

```bash
# 检查安装的包
pip list

# 检查项目是否可导入
python -c "import backend; import frontend; import shared; print('安装成功！')"
```

## 使用 Makefile（可选）

项目提供了 Makefile 来简化常用操作：

```bash
# 查看所有可用命令
make help

# 安装开发依赖
make install-dev

# 运行测试
make test

# 格式化代码
make format

# 代码检查
make lint

# 启动后端
make run-backend

# 启动前端
make run-frontend

# 统一启动
make run
```

## 项目结构

安装后，项目结构如下：

```
hou-cli/
├── backend/          # 后端模块（已安装为包）
├── frontend/         # 前端模块（已安装为包）
├── shared/           # 共享模块（已安装为包）
├── pyproject.toml    # 项目配置
└── ...
```

## 开发工作流

### 1. 日常开发

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装开发依赖（首次）
make install-dev

# 启动开发服务器
# 终端 1
make run-backend

# 终端 2
make run-frontend
```

### 2. 代码质量

```bash
# 格式化代码
make format

# 检查代码格式
make format-check

# 代码检查
make lint

# 运行测试
make test
```

### 3. 添加新依赖

编辑 `pyproject.toml` 的 `dependencies` 或 `[project.optional-dependencies.dev]` 部分：

```toml
[project]
dependencies = [
    # ... 现有依赖
    "new-package>=1.0.0",  # 添加新依赖
]
```

然后重新安装：

```bash
pip install -e ".[dev]"
```

## 环境变量配置

创建 `.env` 文件：

```bash
# LLM 配置
DEEPSEEK_API_KEY=your_api_key_here
OLLAMA_MODEL=deepseek-r1:14b

# 后端配置
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# 日志配置
LOG_LEVEL=INFO
```

## 常见问题

### 1. 安装失败

如果安装失败，尝试：

```bash
# 升级 pip
pip install --upgrade pip

# 升级构建工具
pip install --upgrade setuptools wheel

# 重新安装
pip install -e ".[dev]"
```

### 2. 导入错误

确保项目已正确安装：

```bash
# 检查是否在虚拟环境中
which python  # 应该指向 venv/bin/python

# 重新安装项目
pip install -e .
```

### 3. 依赖冲突

如果遇到依赖冲突：

```bash
# 查看冲突
pip check

# 创建新的虚拟环境
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## 与 requirements.txt 的关系

虽然项目使用 `pyproject.toml` 作为主要配置，但 `requirements.txt` 仍然保留用于：

1. **兼容性**：某些工具可能只支持 requirements.txt
2. **CI/CD**：某些 CI 系统可能更熟悉 requirements.txt
3. **备用方案**：如果 pyproject.toml 有问题，可以使用 requirements.txt

两者保持同步，但 `pyproject.toml` 是主要配置源。

## 最佳实践

1. ✅ **始终使用虚拟环境**
2. ✅ **使用 `pip install -e ".[dev]"` 安装开发依赖**
3. ✅ **定期更新依赖**：`pip install --upgrade -e ".[dev]"`
4. ✅ **提交前运行**：`make format-check && make lint && make test`
5. ✅ **使用 Makefile** 简化常用操作

## 下一步

- 查看 [依赖管理文档](./dependency-management.md) 了解更多细节
- 查看 [架构设计文档](./architecture-design.md) 了解项目结构
- 查看 [快速参考](./quick-reference.md) 了解核心概念











