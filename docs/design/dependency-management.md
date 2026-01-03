# 依赖管理指南

## 概述

本项目使用标准的 Python 依赖管理方案，支持多种安装和管理方式。

## Python 版本要求

- **最低版本**：Python 3.10
- **推荐版本**：Python 3.11 或 3.12
- **版本文件**：`.python-version`（用于 pyenv）

## 依赖管理文件

### 1. requirements.txt

生产环境依赖，包含运行项目所需的所有核心库。

**安装方式**：
```bash
pip install -r requirements.txt
```

### 2. requirements-dev.txt

开发环境依赖，包含测试、代码质量检查、打包等工具。

**安装方式**：
```bash
pip install -r requirements-dev.txt
```

### 3. pyproject.toml

现代 Python 项目配置文件，支持：
- 项目元数据
- 依赖声明
- 工具配置（black, isort, mypy, pytest）
- 可选的开发依赖组

**安装方式**：
```bash
# 安装项目（开发模式）
pip install -e .

# 安装项目 + 开发依赖
pip install -e ".[dev]"
```

## 推荐的工作流程

### 方案 1：使用虚拟环境 + requirements.txt（推荐）

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 开发时安装开发依赖
pip install -r requirements-dev.txt
```

### 方案 2：使用 pyenv + pyproject.toml

```bash
# 1. 安装 Python 版本（如果使用 pyenv）
pyenv install 3.11.0
pyenv local 3.11.0

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 3. 安装项目（开发模式）
pip install -e ".[dev]"
```

### 方案 3：使用 Poetry（可选）

如果团队偏好使用 Poetry：

```bash
# 1. 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 2. 初始化项目（如果还没有 pyproject.toml）
poetry init

# 3. 安装依赖
poetry install

# 4. 激活虚拟环境
poetry shell
```

## 依赖分类

### 核心依赖

- **FastAPI + Uvicorn**：后端 API 服务器
- **Rich**：前端 Rich UI 组件
- **Click**：CLI 命令框架
- **httpx**：HTTP 客户端（IPC 通信）
- **Pydantic**：数据验证

### LLM 相关

- **openai**：OpenAI 兼容 API（用于 DeepSeek）
- **langchain**：LLM 应用框架
- **langchain-community**：LangChain 社区扩展
- **langchain-ollama**：Ollama 本地 LLM 支持

### 向量数据库

- **chromadb**：Chroma 向量数据库

### 文档处理

- **pypdf**：PDF 处理
- **pdfplumber**：PDF 文本提取

### 系统工具

- **psutil**：进程和资源管理（代码执行安全）

### 开发工具

- **pytest**：测试框架
- **black**：代码格式化
- **isort**：导入排序
- **flake8**：代码检查
- **mypy**：类型检查
- **pyinstaller**：打包工具

## 更新依赖

### 更新 requirements.txt

```bash
# 1. 更新包
pip install --upgrade <package-name>

# 2. 生成新的 requirements.txt
pip freeze > requirements.txt

# 或者使用 pip-tools（推荐）
pip install pip-tools
pip-compile requirements.in  # 如果有 requirements.in
```

### 更新 pyproject.toml

直接编辑 `pyproject.toml` 中的版本号，然后：

```bash
pip install -e ".[dev]" --upgrade
```

## 依赖锁定（可选）

### 使用 pip-tools

```bash
# 1. 创建 requirements.in
# 2. 编译生成 requirements.txt
pip-compile requirements.in

# 3. 更新依赖
pip-compile --upgrade requirements.in
```

### 使用 Poetry

```bash
# 生成锁定文件
poetry lock

# 更新依赖
poetry update
```

## 环境变量

创建 `.env` 文件（不要提交到 Git）：

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

### 1. 依赖冲突

如果遇到依赖冲突：

```bash
# 查看冲突的包
pip check

# 使用虚拟环境隔离
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 平台特定依赖

某些依赖可能有平台特定版本：

```bash
# 例如：psutil 在不同平台可能需要不同版本
# 在 requirements.txt 中可以使用条件安装
# 或者使用 pyproject.toml 的 platform 标记
```

### 3. 可选依赖

某些依赖是可选的（如向量数据库）：

```txt
# requirements.txt
# 如果需要使用 FAISS
faiss-cpu>=1.7.4; sys_platform != "darwin"
faiss-cpu>=1.7.4; sys_platform == "darwin"
```

## 最佳实践

1. **使用虚拟环境**：始终在虚拟环境中安装依赖
2. **固定版本**：生产环境使用固定版本号
3. **定期更新**：定期更新依赖以获取安全补丁
4. **测试兼容性**：更新依赖后运行测试
5. **文档化**：记录重要的依赖变更

## 依赖检查

```bash
# 检查过时的包
pip list --outdated

# 检查安全漏洞（需要 pip-audit）
pip install pip-audit
pip-audit

# 检查依赖树
pip list --tree
```

## 总结

- ✅ 使用 `requirements.txt` 管理生产依赖
- ✅ 使用 `requirements-dev.txt` 管理开发依赖
- ✅ 使用 `pyproject.toml` 提供现代项目配置
- ✅ 使用虚拟环境隔离依赖
- ✅ 定期更新和维护依赖


