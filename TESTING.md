# 测试指南

## 快速开始

### 1. 运行单元测试（Mock）

```bash
# 测试上下文管理器
python tests/test_context_manager_quick.py

# 测试端到端对话（Mock）
python tests/test_e2e_chat.py

# 测试多轮对话上下文（Mock）
python tests/test_multi_turn_chat.py

# 或运行所有测试
chmod +x tests/test_all.sh
./tests/test_all.sh
```

### 2. 实际端到端测试

#### 步骤 1: 配置环境变量

```bash
# 复制模板文件
cp env.example .env

# 编辑 .env 文件，设置你的 DeepSeek API Key
# DEEPSEEK_API_KEY=your_actual_api_key_here
```

#### 步骤 2: 启动后端

**终端 1**:
```bash
# 方法 1: 直接启动
python -m backend.main

# 方法 2: 使用统一脚本（后台运行）
python cli.py start

# 方法 3: 使用 Makefile
make start
```

**验证后端启动**:
- 看到 "后端服务启动在 http://127.0.0.1:{port}" 消息
- 可以访问健康检查: `curl http://127.0.0.1:{port}/health`

#### 步骤 3: 启动前端测试

**终端 2**:
```bash
# 单次对话（非流式）
python -m frontend.main chat "你好，你是谁？" --no-stream

# 单次对话（流式）
python -m frontend.main chat "你好，你是谁？"

# 交互式对话（多轮对话测试）
python -m frontend.main chat
```

---

## 多轮对话上下文测试

### 测试场景

在交互式模式下（`python -m frontend.main chat`），进行以下测试：

#### 场景 1: 基础上下文测试

```
你: 你好，我的名字是张三
Agent: [回复并记住名字]

你: 你还记得我的名字吗？
Agent: [应该回答"张三"或相关内容] ✅

你: 很好，谢谢
Agent: [理解上下文] ✅
```

#### 场景 2: 复杂上下文测试

```
你: 我喜欢编程，特别是 Python
Agent: [回复]

你: 我刚才说我喜欢什么语言？
Agent: [应该回答"Python"] ✅

你: 很好，那你能帮我写代码吗？
Agent: [理解上下文，知道是编程相关] ✅
```

#### 场景 3: 历史消息限制测试

```
# 进行超过 10 轮对话
你: 消息1
Agent: 回复1
你: 消息2
Agent: 回复2
...
你: 消息15
Agent: 回复15

# 验证：Agent 应该只记住最近 10 条消息
你: 我刚才说的第一条消息是什么？
Agent: [应该不记得"消息1"，因为已被丢弃] ✅
```

---

## 验证检查清单

### 功能验证
- [ ] 后端服务可以正常启动
- [ ] 前端可以成功连接到后端
- [ ] 非流式对话功能正常
- [ ] 流式对话功能正常
- [ ] 交互式对话功能正常

### 上下文验证
- [ ] 会话 ID 正确显示（交互式模式）
- [ ] 多轮对话上下文正常（Agent 能记住之前的对话）
- [ ] 历史消息正确保存（最多 10 条）
- [ ] 超过 10 条消息时，最旧的消息被丢弃

### 错误处理验证
- [ ] 后端未启动时，前端显示友好错误提示
- [ ] API Key 无效时，显示明确错误信息
- [ ] 网络错误时，有重试机制

---

## 故障排查

### 后端启动失败
1. 检查 `.env` 文件是否存在
2. 检查 `DEEPSEEK_API_KEY` 是否设置
3. 验证 API Key 格式（长度至少 10 个字符）

### 前端连接失败
1. 确认后端已启动
2. 检查端口文件是否存在
3. 检查端口文件内容是否正确

### 上下文不工作
1. 检查前端是否生成 `session_id`
2. 检查后端是否正确接收 `session_id`
3. 查看后端日志确认历史消息

---

## 测试脚本说明

### test_context_manager_quick.py
快速测试上下文管理器的基础功能：
- 会话创建
- 消息添加
- 历史限制
- 多轮对话

### tests/test_e2e_chat.py
端到端对话测试（使用 Mock）：
- Orchestrator 上下文管理
- 流式响应上下文管理
- 历史消息验证

### tests/test_multi_turn_chat.py
多轮对话上下文测试（使用 Mock）：
- 多轮对话上下文保持
- 历史消息内容验证
- 上下文连贯性验证

---

**创建时间**: 2025-12-31

