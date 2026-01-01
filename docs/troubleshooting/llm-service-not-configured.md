# 故障排查：LLM 服务未配置

## 问题描述

启动前端后，发送消息时收到错误：
```
Agent: LLM 服务未配置
```

## 原因分析

这个问题通常是因为 `DEEPSEEK_API_KEY` 环境变量未设置或未正确加载。

可能的原因：
1. `.env` 文件不存在
2. `.env` 文件中没有设置 `DEEPSEEK_API_KEY`
3. API Key 格式无效（长度不足）
4. 后端启动时 `.env` 文件未正确加载

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

1. **检查后端启动日志**:
   - 如果 API Key 未设置，后端启动时会抛出 `ValueError`
   - 如果 API Key 格式无效，也会抛出 `ValueError`

2. **检查前端连接**:
   - 前端能连接到后端说明后端已启动
   - 如果收到 "LLM 服务未配置"，说明后端启动时 API Key 检查通过了，但可能是在运行时检查失败

3. **检查 API Key 格式**:
   - API Key 长度至少 10 个字符
   - 不能为空字符串

## 常见错误

### 错误 1: "DEEPSEEK_API_KEY 环境变量未设置"
**原因**: `.env` 文件不存在或未设置 API Key

**解决**: 创建 `.env` 文件并设置 `DEEPSEEK_API_KEY`

### 错误 2: "API Key 格式无效：长度不足或为空"
**原因**: API Key 为空或长度不足 10 个字符

**解决**: 检查 API Key 是否正确复制，确保没有多余空格

### 错误 3: 后端启动成功但前端显示 "LLM 服务未配置"
**原因**: 可能是代码中的检查逻辑问题

**解决**: 
- 检查 `backend/services/llm/llm_service.py` 中的初始化逻辑
- 确保 `.env` 文件在 `Orchestrator` 创建之前已加载

## 代码修复

如果问题持续存在，检查以下文件：

1. `backend/main.py` - 确保在导入路由前加载 `.env`
2. `backend/api/routes.py` - 确保在创建 `Orchestrator` 前加载 `.env`
3. `backend/core/agent/orchestrator.py` - 确保在创建 `LLMService` 前加载 `.env`

---

**最后更新**: 2025-12-31

