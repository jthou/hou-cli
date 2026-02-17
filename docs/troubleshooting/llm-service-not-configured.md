# 故障排查：LLM 服务配置错误

## 问题描述

启动前端后，发送消息时收到错误。常见的错误消息包括：

**错误 1**：
```
错误: DEEPSEEK_API_KEY 环境变量未设置
```

**错误 2**：
```
错误: API Key 格式无效：长度不足或为空
```

**错误 3**（流式响应）：
```
Agent: [显示错误消息]
```

## 原因分析

这个问题通常是因为 `DEEPSEEK_API_KEY` 环境变量未设置或未正确加载。

可能的原因：
1. `.env` 文件不存在
2. `.env` 文件中没有设置 `DEEPSEEK_API_KEY`
3. API Key 格式无效（长度不足 10 个字符或为空）
4. `.env` 文件未正确加载（虽然代码中已在多处加载）

## 解决方案

### 方案 1: 创建并配置 .env 文件（推荐）

```bash
# 1. 复制模板文件
cp env.example .env

# 2. 编辑 .env 文件，设置你的 API Key
# DEEPSEEK_API_KEY=your_actual_api_key_here

# 3. 重启后端服务
python -m backend.main
```

### 方案 2: 使用系统环境变量

```bash
# Linux/macOS
export DEEPSEEK_API_KEY=your_actual_api_key_here
python -m backend.main

# Windows
set DEEPSEEK_API_KEY=your_actual_api_key_here
python -m backend.main
```

### 方案 3: 验证配置

```bash
# 检查 .env 文件是否存在
ls -la .env

# 检查 .env 文件内容（不显示敏感信息）
grep -E "^DEEPSEEK_API_KEY=" .env | sed 's/=.*/=***/'

# 检查环境变量是否设置
python -c "import os; print('API Key 已设置' if os.environ.get('DEEPSEEK_API_KEY') else 'API Key 未设置')"
```

## 验证步骤

1. **检查后端启动**:
   - 后端启动时不会立即检查 API Key（因为 `Orchestrator` 是延迟创建的）
   - 后端启动成功只说明 FastAPI 服务器已启动，不意味着 API Key 已配置

2. **检查第一次 API 调用**:
   - 第一次调用 `/api/chat` 或 `/api/chat/stream` 时，会创建 `Orchestrator` 实例
   - `Orchestrator` 初始化时会创建 `LLMService`，此时会检查 API Key
   - 如果 API Key 未设置或格式无效，会抛出 `ValueError` 异常
   - 异常会被捕获并返回给前端，前端会显示具体的错误消息

3. **检查 API Key 格式**:
   - API Key 长度至少 10 个字符
   - 不能为空字符串或只包含空格

## 常见错误

### 错误 1: "DEEPSEEK_API_KEY 环境变量未设置"

**发生时机**: 第一次调用 API 时（`Orchestrator` 初始化时）

**原因**: 
- `.env` 文件不存在
- `.env` 文件中没有设置 `DEEPSEEK_API_KEY`
- `.env` 文件路径不正确

**解决步骤**:
1. 检查 `.env` 文件是否存在：`ls -la .env`（Linux/macOS）或 `dir .env`（Windows）
2. 如果不存在，复制模板：`cp env.example .env`
3. 编辑 `.env` 文件，设置 `DEEPSEEK_API_KEY=your_actual_api_key_here`
4. 重启后端服务

### 错误 2: "API Key 格式无效：长度不足或为空"

**发生时机**: 第一次调用 API 时（`LLMService` 初始化时）

**原因**: 
- API Key 为空字符串
- API Key 长度不足 10 个字符
- API Key 只包含空格（会被 `strip()` 处理为空）

**解决步骤**:
1. 检查 API Key 是否正确复制（确保没有多余空格）
2. 验证 API Key 长度：`python -c "import os; from dotenv import load_dotenv; load_dotenv(); key = os.getenv('DEEPSEEK_API_KEY', ''); print(f'长度: {len(key.strip())}')"`
3. 确保 API Key 至少 10 个字符
4. 重新设置 API Key 并重启后端

### 错误 3: 后端启动成功但 API 调用失败

**现象**: 
- 后端启动时没有报错
- 前端可以连接到后端（健康检查通过）
- 但发送消息时收到错误

**原因**: 
- `Orchestrator` 是延迟创建的（单例模式）
- 后端启动时不会立即创建 `LLMService`
- 只有在第一次 API 调用时才会检查 API Key

**解决**: 按照错误 1 或错误 2 的解决方案处理

## 代码实现说明

当前代码已在多处加载 `.env` 文件，确保 API Key 能够正确读取：

1. **`backend/main.py`** (第 11-16 行)
   - 在启动 FastAPI 应用前加载 `.env`
   - 确保环境变量在应用启动时可用

2. **`backend/api/routes.py`** (第 12-17 行)
   - 在导入 `Orchestrator` 之前加载 `.env`
   - 确保路由模块导入时环境变量已加载

3. **`backend/core/agent/orchestrator.py`** (第 8-13 行)
   - 在导入 `LLMService` 之前加载 `.env`
   - 确保 Agent 模块导入时环境变量已加载

4. **`backend/services/llm/llm_service.py`** (第 23-30 行)
   - `LLMService.__init__()` 中检查 API Key
   - 如果未设置，抛出 `ValueError("DEEPSEEK_API_KEY 环境变量未设置")`
   - 如果格式无效，抛出 `ValueError("API Key 格式无效：长度不足或为空")`

5. **`backend/api/routes.py`** (第 59-64 行, 第 81-82 行)
   - 异常处理：捕获所有异常并返回错误信息
   - 非流式：返回 `{"status": "error", "error": str(e)}`
   - 流式：返回 SSE 格式的错误消息

## 调试技巧

### 检查环境变量是否加载成功

```bash
# 方法 1: 使用 Python 检查
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key:', '已设置' if os.getenv('DEEPSEEK_API_KEY') else '未设置')"

# 方法 2: 检查 .env 文件内容（隐藏敏感信息）
grep -E "^DEEPSEEK_API_KEY=" .env | sed 's/=.*/=***/'

# 方法 3: 检查 API Key 长度
python -c "from dotenv import load_dotenv; import os; load_dotenv(); key = os.getenv('DEEPSEEK_API_KEY', ''); print(f'长度: {len(key.strip())}')"
```

### 查看后端日志

如果后端在前台运行，可以看到详细的错误信息：

```bash
# 前台运行后端（可以看到日志）
python -m backend.main

# 或使用 Make
make run-backend
```

### 测试 API Key 配置

端口文件位置（跨平台）：
- **macOS**: `~/Library/Application Support/hou-cli/port.txt`
- **Linux**: `~/.local/share/hou-cli/port.txt`
- **Windows**: `%LOCALAPPDATA%\hou-cli\port.txt`

```bash
# 方法 1: 使用 Python 获取端口（跨平台）
PORT=$(python -c "from shared.platform_utils import load_port; print(load_port())" 2>/dev/null || echo 8000)

# 测试后端健康检查
curl http://127.0.0.1:${PORT}/health

# 测试聊天 API（需要先启动后端）
curl -X POST http://127.0.0.1:${PORT}/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "测试"}'

# 方法 2: 直接读取端口文件（macOS）
curl http://127.0.0.1:$(cat ~/Library/Application\ Support/hou-cli/port.txt 2>/dev/null || echo 8000)/health

# 方法 2: 直接读取端口文件（Linux）
curl http://127.0.0.1:$(cat ~/.local/share/hou-cli/port.txt 2>/dev/null || echo 8000)/health
```

---

**最后更新**: 2025-01-02  
**状态**: ✅ 已修复 - 代码中已实现完整的错误检查和提示
















