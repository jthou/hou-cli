# TODO-001 TDD 测试状态

## TDD 流程说明

**TDD (Test-Driven Development) 流程**:
1. 🔴 **Red**: 先写测试，测试失败（当前阶段）
2. 🟢 **Green**: 实现功能，让测试通过
3. 🔵 **Refactor**: 重构代码，保持测试通过

---

## 当前状态：🔴 Red 阶段

### 新增测试用例列表

#### LLM Service 测试 (`backend/services/llm/tests/test_llm_service.py`)

**配置管理测试**:
- [ ] `test_config_missing_api_key` - ❌ **失败** - 需要实现 API Key 验证
- [ ] `test_config_invalid_api_key_format` - ❌ **失败** - 需要实现 API Key 格式验证

**错误处理测试**:
- [ ] `test_chat_401_error_no_retry` - ❌ **失败** - 需要实现 401 错误处理（不重试）
- [ ] `test_chat_429_error_with_retry` - ❌ **失败** - 需要实现 429 错误处理（等待后重试）
- [ ] `test_chat_network_error_with_retry` - ❌ **失败** - 需要实现网络错误重试机制
- [ ] `test_chat_retry_exhausted` - ❌ **失败** - 需要实现重试次数限制

**参数配置测试**:
- [ ] `test_temperature_parameter_validation` - ❌ **失败** - 需要实现 temperature 参数支持
- [ ] `test_max_tokens_parameter_validation` - ❌ **失败** - 需要实现 max_tokens 参数支持
- [ ] `test_chat_with_parameters` - ❌ **失败** - 需要实现参数传递

**流式响应测试**:
- [ ] `test_stream_chat_timeout` - ❌ **失败** - 需要实现流式响应超时控制
- [ ] `test_stream_chat_interrupt_handling` - ❌ **失败** - 需要实现流式响应中断处理

#### 集成测试 (`tests/test_integration_deepseek.py`)

**端到端测试**:
- [ ] `test_e2e_chat_flow` - ⚠️ **待实现** - 需要完整的端到端测试框架
- [ ] `test_e2e_stream_chat_flow` - ⚠️ **待实现** - 需要完整的端到端测试框架

**上下文管理测试**:
- [ ] `test_session_id_generation` - ⚠️ **待实现** - 需要实现会话 ID 管理
- [ ] `test_session_context_isolation` - ⚠️ **待实现** - 需要实现会话上下文隔离
- [ ] `test_history_limit` - ⚠️ **待实现** - 需要实现历史消息限制

---

## 实现优先级

### 阶段 1: 配置管理（高优先级）
1. ✅ 测试已编写：`test_config_missing_api_key`
2. ✅ 测试已编写：`test_config_invalid_api_key_format`
3. ⏳ **待实现**：API Key 验证逻辑

### 阶段 2: 错误处理（高优先级）
1. ✅ 测试已编写：`test_chat_401_error_no_retry`
2. ✅ 测试已编写：`test_chat_429_error_with_retry`
3. ✅ 测试已编写：`test_chat_network_error_with_retry`
4. ✅ 测试已编写：`test_chat_retry_exhausted`
5. ⏳ **待实现**：错误处理和重试机制

### 阶段 3: 参数配置（中优先级）
1. ✅ 测试已编写：`test_temperature_parameter_validation`
2. ✅ 测试已编写：`test_max_tokens_parameter_validation`
3. ✅ 测试已编写：`test_chat_with_parameters`
4. ⏳ **待实现**：参数配置支持

### 阶段 4: 流式响应优化（中优先级）
1. ✅ 测试已编写：`test_stream_chat_timeout`
2. ✅ 测试已编写：`test_stream_chat_interrupt_handling`
3. ⏳ **待实现**：流式响应超时和中断处理

### 阶段 5: 上下文管理（低优先级）
1. ✅ 测试已编写：`test_session_id_generation`
2. ✅ 测试已编写：`test_session_context_isolation`
3. ✅ 测试已编写：`test_history_limit`
4. ⏳ **待实现**：上下文管理功能

---

## 测试运行命令

### 运行所有新增测试（预期全部失败）
```bash
# 运行配置管理测试
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_config_missing_api_key -v -s
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_config_invalid_api_key_format -v -s

# 运行错误处理测试
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_chat_401_error_no_retry -v -s
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_chat_429_error_with_retry -v -s
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_chat_network_error_with_retry -v -s
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_chat_retry_exhausted -v -s

# 运行参数配置测试
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_temperature_parameter_validation -v -s
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_max_tokens_parameter_validation -v -s
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_chat_with_parameters -v -s

# 运行流式响应测试
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_stream_chat_timeout -v -s
pytest backend/services/llm/tests/test_llm_service.py::TestLLMService::test_stream_chat_interrupt_handling -v -s
```

### 运行所有测试查看状态
```bash
pytest backend/services/llm/tests/test_llm_service.py -v --tb=line
```

---

## 下一步：实现功能（🟢 Green 阶段）

按照优先级逐步实现功能，让测试通过：

1. **实现配置管理**
   - 修改 `LLMService.__init__()` 添加 API Key 验证
   - 添加格式验证逻辑

2. **实现错误处理**
   - 修改 `LLMService.chat()` 添加重试机制
   - 实现 401、429、网络错误的特殊处理

3. **实现参数配置**
   - 修改 `LLMService.__init__()` 支持参数
   - 修改 `LLMService.chat()` 传递参数

4. **实现流式响应优化**
   - 修改 `LLMService.stream_chat()` 添加超时控制
   - 实现中断处理

5. **实现上下文管理**
   - 在 Orchestrator 或 API 层实现会话管理
   - 实现历史消息限制

---

## 测试覆盖率目标

- 当前：约 33%
- 目标：> 80%（实现后）

---

**创建时间**: 2025-12-31  
**当前阶段**: 🔴 Red (测试编写完成，等待实现)

