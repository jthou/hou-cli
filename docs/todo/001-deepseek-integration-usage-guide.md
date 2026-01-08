# TODO-001 使用指南

## 概述

本文档提供 TODO-001（DeepSeek 集成与主 Agent 数据流）的详细使用指南，包括快速开始、配置说明、常见问题和故障排除。

**创建时间**: 2025-01-01  
**适用版本**: v1.0  
**相关文档**: 
- [001-deepseek-integration.md](./001-deepseek-integration.md) - 主任务文档
- [001-deepseek-integration-test-guide.md](./001-deepseek-integration-e2e-test-guide.md) - 测试指南

---

## 一、快速开始

### 1.1 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 1.2 配置 API Key

```bash
# 复制示例文件
cp env.example .env

# 编辑 .env 文件，设置你的 DeepSeek API Key
# DEEPSEEK_API_KEY=your_api_key_here
```

### 1.3 启动服务

**方式 1: 使用 Makefile（推荐）**
```bash
make start
```

**方式 2: 手动启动**
```bash
# 终端 1: 启动后端
python -m backend.main

# 终端 2: 启动前端
python -m frontend.main chat
```

### 1.4 开始使用

启动后，在交互式界面中输入消息即可开始对话：

```
你: 你好
Agent: 你好！很高兴见到你！😊
```

---

## 二、配置说明

### 2.1 环境变量配置

#### `.env` 文件配置

创建 `.env` 文件（参考 `env.example`）：

```bash
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_api_key_here

# 可选配置
DEEPSEEK_BASE_URL=https://api.deepseek.com  # 默认值
```

#### 环境变量说明

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | - | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | ❌ | `https://api.deepseek.com` | API 基础 URL |

### 2.2 LLM 服务参数配置

在代码中配置 LLM 服务参数：

```python
from backend.services.llm.llm_service import LLMService

# 创建服务实例，自定义参数
service = LLMService(
    temperature=0.7,  # 温度参数 (0.0-2.0)，控制输出随机性
    max_tokens=2000   # 最大 token 数
)
```

**参数说明**:
- `temperature`: 控制输出的随机性
  - `0.0`: 完全确定性输出
  - `0.7`: 默认值，平衡创造性和准确性
  - `2.0`: 最大随机性
- `max_tokens`: 限制响应长度
  - 默认: `2000`
  - 范围: `> 0`

---

## 三、使用场景

### 3.1 非流式对话

**适用场景**: 需要完整响应后再显示

```bash
# 命令行模式
python -m frontend.main chat "你好" --no-stream

# 交互式模式（启动后输入）
python -m frontend.main chat
# 然后输入消息
```

### 3.2 流式对话（默认）

**适用场景**: 实时显示响应，提升用户体验

```bash
# 命令行模式（默认流式）
python -m frontend.main chat "请写一首诗"

# 交互式模式（默认流式）
python -m frontend.main chat
```

### 3.3 多轮对话

**功能**: 自动维护对话上下文

```bash
# 启动交互式模式
python -m frontend.main chat

# 第一轮
你: 我的名字是张三
Agent: 你好，张三！

# 第二轮（自动使用上下文）
你: 你还记得我的名字吗？
Agent: 当然记得，你的名字是张三。
```

**说明**:
- 会话 ID 自动生成和管理
- 自动维护最近 10 条消息的历史
- 上下文自动传递给 LLM

---

## 四、常见问题

### Q1: 后端启动失败，提示 "DEEPSEEK_API_KEY 环境变量未设置"

**原因**: API Key 未配置或配置不正确

**解决方案**:
1. 检查 `.env` 文件是否存在
2. 确认 `DEEPSEEK_API_KEY` 已设置
3. 检查 `.env` 文件格式是否正确（无多余空格）

```bash
# 验证配置
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key:', '已设置' if os.getenv('DEEPSEEK_API_KEY') else '未设置')"
```

### Q2: 前端无法连接到后端

**原因**: 后端未启动或端口被占用

**解决方案**:
1. 确认后端已启动（检查终端 1）
2. 检查后端日志是否有错误
3. 检查端口是否被占用

```bash
# 检查端口占用（Linux/Mac）
lsof -i :8000

# 检查端口占用（Windows）
netstat -ano | findstr :8000
```

### Q3: 流式输出有重复字符

**原因**: 流式渲染逻辑问题（已在 TODO-003 中修复）

**解决方案**:
1. 确认已更新到最新版本
2. 检查 `frontend/ui/stream_handler.py` 是否为最新版本
3. 如果问题仍存在，请提交 Issue

### Q4: 多轮对话上下文不工作

**原因**: 会话 ID 未正确传递或上下文管理器未正常工作

**解决方案**:
1. 检查会话 ID 是否正确显示
2. 查看后端日志，确认 `ContextManager` 是否正常工作
3. 检查 `Orchestrator` 是否正确使用上下文

```bash
# 查看后端日志
# 应该能看到类似以下日志：
# INFO: 创建新会话: session_id=xxx
# INFO: 获取历史消息: session_id=xxx, count=2
```

### Q5: API 调用返回 401 错误

**原因**: API Key 无效或已过期

**解决方案**:
1. 检查 API Key 是否正确
2. 确认 API Key 是否有效
3. 检查 API Key 是否有使用限制

### Q6: 流式响应超时

**原因**: 响应时间过长或网络问题

**解决方案**:
1. 检查网络连接
2. 增加超时时间（默认 60 秒）
3. 检查 API 服务状态

---

## 五、故障排除

### 5.1 后端启动问题

**问题**: 后端启动失败

**排查步骤**:
1. 检查 Python 版本（需要 3.10+）
2. 检查依赖是否安装完整
3. 检查 API Key 配置
4. 查看错误日志

```bash
# 检查 Python 版本
python --version

# 检查依赖
pip list | grep -E "fastapi|uvicorn|openai"

# 查看详细错误
python -m backend.main --verbose
```

### 5.2 前端连接问题

**问题**: 前端无法连接到后端

**排查步骤**:
1. 确认后端已启动
2. 检查端口文件是否存在
3. 检查防火墙设置
4. 查看前端错误日志

```bash
# 检查端口文件
cat ~/.hou-cli/port.txt  # Linux/Mac
type %APPDATA%\hou-cli\port.txt  # Windows

# 检查后端健康状态
curl http://127.0.0.1:8000/health
```

### 5.3 API 调用问题

**问题**: API 调用失败

**排查步骤**:
1. 检查 API Key 有效性
2. 检查网络连接
3. 查看 API 错误响应
4. 检查 API 服务状态

```bash
# 测试 API Key（使用 curl）
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

### 5.4 性能问题

**问题**: 响应慢或卡顿

**排查步骤**:
1. 检查网络延迟
2. 检查系统资源使用
3. 检查 API 服务状态
4. 优化参数配置

```bash
# 检查系统资源
top  # Linux/Mac
taskmgr  # Windows

# 检查网络延迟
ping api.deepseek.com
```

---

## 六、高级用法

### 6.1 自定义 LLM 服务参数

```python
from backend.services.llm.llm_service import LLMService

# 创建自定义服务实例
service = LLMService(
    temperature=0.9,  # 更高的创造性
    max_tokens=4000   # 更长的响应
)
```

### 6.2 错误处理

系统自动处理以下错误：
- **401 错误**: 认证失败，不重试
- **429 错误**: 限流，等待 2 秒后重试
- **网络错误**: 重试 3 次，间隔 1 秒
- **超时错误**: 流式响应超时（默认 60 秒）

### 6.3 日志配置

```python
import logging

# 配置日志级别
logging.basicConfig(level=logging.INFO)

# 查看详细日志
logging.getLogger('backend.services.llm').setLevel(logging.DEBUG)
```

---

## 七、最佳实践

### 7.1 配置管理
- ✅ 使用 `.env` 文件管理敏感信息
- ✅ 不要将 `.env` 文件提交到版本控制
- ✅ 使用 `env.example` 作为模板

### 7.2 错误处理
- ✅ 检查 API Key 配置
- ✅ 处理网络错误
- ✅ 监控 API 调用失败率

### 7.3 性能优化
- ✅ 使用流式响应提升用户体验
- ✅ 合理设置 `max_tokens` 限制响应长度
- ✅ 根据场景调整 `temperature` 参数

---

## 八、相关资源

### 8.1 文档
- [架构设计文档](../../design/architecture-design.md)
- [流式响应设计](../../design/streaming-response.md)
- [环境配置文档](../../design/env-configuration.md)

### 8.2 代码
- `backend/services/llm/llm_service.py` - LLM 服务实现
- `backend/core/agent/orchestrator.py` - 主 Agent 编排器
- `frontend/main.py` - 前端主程序

### 8.3 测试
- [测试指南](./001-deepseek-integration-e2e-test-guide.md)
- [测试报告](./001-deepseek-integration-test-report.md)

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 1.0









