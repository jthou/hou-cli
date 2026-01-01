# 前后端集成测试指南

## 测试步骤

### 步骤 1: 运行单元测试

```bash
# 运行上下文管理器测试
python tests/test_context_manager_quick.py

# 运行端到端测试（Mock）
python tests/test_e2e_chat.py

# 运行多轮对话测试（Mock）
python tests/test_multi_turn_chat.py

# 或运行所有测试
chmod +x tests/test_all.sh
./tests/test_all.sh
```

### 步骤 2: 启动后端服务

**终端 1**:
```bash
# 确保 .env 文件存在并配置了 DEEPSEEK_API_KEY
cp env.example .env
# 编辑 .env 文件，设置你的 API Key

# 启动后端
python -m backend.main

# 或使用统一启动脚本
python cli.py start

# 或使用 Makefile
make start
```

**验证后端启动**:
- 看到 "后端服务启动在 http://127.0.0.1:{port}" 消息
- 端口文件已创建（检查 `~/.local/share/hou-cli/port.txt` 或对应平台路径）

### 步骤 3: 启动前端进行测试

**终端 2**:
```bash
# 单次对话测试（非流式）
python -m frontend.main chat "你好，你是谁？" --no-stream

# 单次对话测试（流式）
python -m frontend.main chat "你好，你是谁？"

# 交互式对话测试（多轮对话）
python -m frontend.main chat
```

### 步骤 4: 验证多轮对话上下文

在交互式模式下进行以下测试：

1. **第一轮对话**:
   ```
   你: 你好，我的名字是张三
   Agent: [应该回复并记住名字]
   ```

2. **第二轮对话（测试上下文）**:
   ```
   你: 你还记得我的名字吗？
   Agent: [应该回答"张三"或相关内容]
   ```

3. **第三轮对话（继续测试）**:
   ```
   你: 很好，谢谢
   Agent: [应该能理解上下文]
   ```

4. **验证上下文**:
   - Agent 应该能记住之前的对话内容
   - 对话应该连贯自然

---

## 测试场景

### 场景 1: 简单问答（非流式）
```bash
python -m frontend.main chat "1+1等于几？" --no-stream
```

**预期结果**:
- 前端显示完整回复
- 回复内容合理

### 场景 2: 简单问答（流式）
```bash
python -m frontend.main chat "1+1等于几？"
```

**预期结果**:
- 前端实时显示流式输出
- 输出流畅无卡顿

### 场景 3: 多轮对话（上下文测试）
```bash
python -m frontend.main chat
```

然后依次输入：
1. "我的名字是张三"
2. "你还记得我的名字吗？"
3. "很好，谢谢"

**预期结果**:
- 每轮对话都能正常响应
- Agent 能记住之前的对话内容
- 对话连贯自然

### 场景 4: 错误处理测试
```bash
# 后端未启动时
python -m frontend.main chat "测试"
```

**预期结果**:
- 显示友好的错误提示
- 提示用户启动后端服务

---

## 故障排查

### 问题 1: 后端启动失败

**可能原因**:
- API Key 未设置或无效
- 端口被占用

**解决方案**:
1. 检查 `.env` 文件是否存在且包含有效的 `DEEPSEEK_API_KEY`
2. 检查端口是否被占用
3. 查看后端启动日志

### 问题 2: 前端无法连接后端

**可能原因**:
- 后端未启动
- 端口文件未创建
- 端口文件路径错误

**解决方案**:
1. 确认后端已启动
2. 检查端口文件是否存在：
   - macOS/Linux: `~/.local/share/hou-cli/port.txt`
   - Windows: `%LOCALAPPDATA%\hou-cli\port.txt`
3. 检查端口文件内容是否正确

### 问题 3: 上下文不工作

**可能原因**:
- 会话 ID 未正确传递
- 历史消息未正确保存

**解决方案**:
1. 检查前端是否生成并传递 `session_id`
2. 检查后端是否正确保存历史消息
3. 查看后端日志确认历史消息是否包含在请求中

---

## 测试检查清单

### 自动化测试（已实现）

- [x] 后端服务可以正常启动 - ✅ 自动化测试：`tests/integration/test_e2e_chat.py::test_backend_health_check`
- [x] 前端可以成功连接到后端 - ✅ 自动化测试：`tests/integration/test_e2e_chat.py::test_frontend_backend_integration_non_stream`
- [x] 非流式对话功能正常 - ✅ 自动化测试：`tests/integration/test_e2e_chat.py::test_frontend_backend_integration_non_stream`
- [x] 流式对话功能正常 - ✅ 自动化测试：`tests/integration/test_e2e_chat.py::test_frontend_backend_integration_stream`
- [x] 多轮对话上下文正常（技术流程） - ✅ 自动化测试：`tests/integration/test_e2e_chat.py::test_multi_turn_conversation`
- [x] 错误处理友好且明确 - ✅ 自动化测试：`tests/integration/test_e2e_chat.py::test_error_handling_backend_not_running`
- [x] 会话 ID 管理 - ✅ 自动化测试：`tests/integration/test_e2e_chat.py::test_session_id_management`

### 手动测试（可选，用于验证用户体验）

- [ ] 交互式对话功能正常（需要手动输入）
- [ ] 多轮对话上下文正常（Agent 能记住之前的对话，需要真实 LLM 响应）
- [ ] 会话 ID 正确显示（交互式模式，需要手动验证）

## 运行自动化测试

```bash
# 运行所有端到端集成测试
pytest tests/integration/test_e2e_chat.py -v

# 运行所有集成测试（包括基础集成测试）
pytest tests/integration/ tests/test_integration.py -v
```

**注意**: 自动化测试会自动启动和清理后端服务，使用 Mock API Key，避免真实 API 调用。

---

**创建时间**: 2025-12-31

