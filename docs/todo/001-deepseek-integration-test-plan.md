# TODO-001 测试验证方案

## 概述

本文档详细说明 TODO-001（DeepSeek 集成与主 Agent 数据流实现）的测试验证方案，包括单元测试、集成测试和手动测试步骤。

**关联任务**: [001-deepseek-integration.md](./001-deepseek-integration.md)  
**创建时间**: 2025-12-31

---

## 一、测试策略

### 1.1 测试金字塔

```
        /\
       /  \     手动测试（少量）
      /____\
     /      \   集成测试（适量）
    /________\
   /          \ 单元测试（大量）
  /____________\
```

### 1.2 测试覆盖范围

- **单元测试**: 覆盖所有核心功能模块
- **集成测试**: 覆盖完整数据流
- **手动测试**: 验证用户体验和边界场景

---

## 二、单元测试方案

### 2.1 LLM Service 测试

#### 测试文件
`backend/services/llm/tests/test_llm_service.py`

#### 测试用例

**2.1.1 配置管理测试**
- [ ] `test_config_missing_api_key` - 测试 API Key 缺失时的错误处理
- [ ] `test_config_invalid_api_key` - 测试无效 API Key 的验证
- [ ] `test_config_valid_api_key` - 测试有效 API Key 的加载

**实现示例**:
```python
def test_config_missing_api_key():
    """测试 API Key 缺失"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
            LLMService()
```

**2.1.2 非流式聊天测试**
- [ ] `test_chat_success` - 测试成功调用
- [ ] `test_chat_with_system_prompt` - 测试带系统提示的调用
- [ ] `test_chat_without_system_prompt` - 测试无系统提示的调用
- [ ] `test_chat_parameter_validation` - 测试参数验证（temperature, max_tokens）

**2.1.3 流式聊天测试**
- [ ] `test_stream_chat_success` - 测试流式调用成功
- [ ] `test_stream_chat_chunks` - 测试流式数据块接收
- [ ] `test_stream_chat_timeout` - 测试流式响应超时

**2.1.4 错误处理测试**
- [ ] `test_chat_network_error` - 测试网络错误和重试
- [ ] `test_chat_401_error` - 测试认证错误（不重试）
- [ ] `test_chat_429_error` - 测试限流错误（等待后重试）
- [ ] `test_chat_500_error` - 测试服务器错误（重试）
- [ ] `test_chat_retry_exhausted` - 测试重试次数耗尽

**实现示例**:
```python
@pytest.mark.asyncio
async def test_chat_429_error():
    """测试 429 限流错误处理"""
    # [MOCK] 使用 Mock 数据模拟 429 错误
    print("[MOCK] 测试使用 Mock 数据: 429 限流错误")
    service = LLMService()
    
    # 第一次返回 429，第二次成功
    with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = [
            httpx.HTTPStatusError("429", request=None, response=Mock(status_code=429)),
            Mock(choices=[Mock(message=Mock(content="成功响应"))])
        ]
        
        result = await service.chat(user_prompt="测试")
        assert result == "成功响应"
        assert mock_create.call_count == 2
        print("[MOCK] 429 错误已处理，等待后重试成功")
```

**2.1.5 参数配置测试**
- [ ] `test_temperature_validation` - 测试 temperature 参数验证（0-2）
- [ ] `test_max_tokens_validation` - 测试 max_tokens 参数验证（> 0）
- [ ] `test_parameter_defaults` - 测试默认参数值

---

### 2.2 Orchestrator 测试

#### 测试文件
`backend/core/agent/tests/test_orchestrator.py`

#### 测试用例

**2.2.1 任务处理测试**
- [ ] `test_process_success` - 测试任务处理成功
- [ ] `test_process_with_context` - 测试带上下文的任务处理
- [ ] `test_process_error_propagation` - 测试错误传播

**2.2.2 流式处理测试**
- [ ] `test_stream_process_success` - 测试流式处理成功
- [ ] `test_stream_process_chunks` - 测试流式数据块
- [ ] `test_stream_process_error` - 测试流式处理错误

---

### 2.3 API 路由测试

#### 测试文件
`backend/api/tests/test_routes.py`

#### 测试用例

**2.3.1 非流式接口测试**
- [ ] `test_chat_endpoint_success` - 测试聊天接口成功
- [ ] `test_chat_endpoint_error` - 测试聊天接口错误处理
- [ ] `test_chat_endpoint_validation` - 测试请求验证

**2.3.2 流式接口测试**
- [ ] `test_chat_stream_endpoint_success` - 测试流式接口成功
- [ ] `test_chat_stream_endpoint_sse_format` - 测试 SSE 格式正确
- [ ] `test_chat_stream_endpoint_error` - 测试流式接口错误处理

**2.3.3 健康检查测试**
- [ ] `test_health_endpoint` - 测试健康检查接口

---

## 三、集成测试方案

### 3.1 端到端数据流测试

#### 测试文件
`tests/test_integration_deepseek.py`（需创建）

#### 测试用例

**3.1.1 非流式完整流程测试**
- [ ] `test_e2e_chat_flow` - 测试前端到后端的完整非流式流程
  - 前端发送消息
  - 后端接收并处理
  - LLM 调用
  - 响应返回前端
  - 前端显示

**实现示例**:
```python
@pytest.mark.asyncio
async def test_e2e_chat_flow():
    """测试端到端非流式聊天流程"""
    # 1. 启动测试后端
    # 2. 创建前端客户端
    # 3. 发送消息
    # 4. 验证响应
    # 5. 清理资源
    pass
```

**3.1.2 流式完整流程测试**
- [ ] `test_e2e_stream_chat_flow` - 测试前端到后端的完整流式流程
  - 前端发送消息
  - 后端流式处理
  - LLM 流式调用
  - 流式响应返回前端
  - 前端实时显示

**3.1.3 错误场景测试**
- [ ] `test_e2e_network_error` - 测试网络错误场景
- [ ] `test_e2e_api_error` - 测试 API 错误场景
- [ ] `test_e2e_timeout` - 测试超时场景

---

### 3.2 上下文管理测试

#### 测试用例

**3.2.1 会话管理测试**
- [ ] `test_session_id_generation` - 测试会话 ID 生成
- [ ] `test_session_context_isolation` - 测试会话上下文隔离
- [ ] `test_history_limit` - 测试历史消息数量限制（最近 10 条）

**3.2.2 上下文传递测试**
- [ ] `test_context_in_request` - 测试请求中的上下文传递
- [ ] `test_context_in_response` - 测试响应中的上下文更新

---

## 四、手动测试方案

### 4.1 功能测试清单

#### 4.1.1 配置管理测试
- [ ] **测试 1**: 未设置 `DEEPSEEK_API_KEY` 环境变量
  - 预期：服务启动失败，显示明确的错误提示
  - 命令：`python -m backend.main`
  - 验证：检查错误消息是否包含 "DEEPSEEK_API_KEY"

- [ ] **测试 2**: 设置无效的 `DEEPSEEK_API_KEY`
  - 预期：API 调用返回 401 错误
  - 命令：`export DEEPSEEK_API_KEY=invalid_key && python -m frontend.main chat "测试"`
  - 验证：检查错误消息

- [ ] **测试 3**: 设置有效的 `DEEPSEEK_API_KEY`
  - 预期：服务正常启动，可以正常调用
  - 命令：`export DEEPSEEK_API_KEY=valid_key && python -m frontend.main chat "你好"`

#### 4.1.2 非流式聊天测试
- [ ] **测试 4**: 基本聊天功能
  - 步骤：
    1. 启动后端：`python -m backend.main`
    2. 启动前端：`python -m frontend.main chat "你好" --no-stream`
  - 预期：返回完整的回复
  - 验证：检查响应是否完整、合理

- [ ] **测试 5**: 长文本输入
  - 步骤：输入较长的消息（> 1000 字符）
  - 预期：正常处理并返回回复
  - 验证：检查响应质量

- [ ] **测试 6**: 特殊字符输入
  - 步骤：输入包含特殊字符的消息（emoji、中文、符号等）
  - 预期：正常处理
  - 验证：检查响应是否正确处理特殊字符

#### 4.1.3 流式聊天测试
- [ ] **测试 7**: 流式输出功能
  - 步骤：
    1. 启动后端：`python -m backend.main`
    2. 启动前端：`python -m frontend.main chat "请写一首诗"`
  - 预期：实时显示流式输出，无卡顿
  - 验证：检查输出是否流畅、实时

- [ ] **测试 8**: 流式输出中断
  - 步骤：在流式输出过程中按 Ctrl+C
  - 预期：优雅中断，不报错
  - 验证：检查是否正常退出

- [ ] **测试 9**: 长时间流式输出
  - 步骤：请求生成长文本（如长文章）
  - 预期：持续流式输出，不中断
  - 验证：检查是否完整输出

#### 4.1.4 错误处理测试
- [ ] **测试 10**: 网络断开场景
  - 步骤：
    1. 启动服务
    2. 断开网络
    3. 发送请求
  - 预期：显示网络错误提示，有重试机制
  - 验证：检查错误消息和重试行为

- [ ] **测试 11**: API 限流场景
  - 步骤：快速发送多个请求
  - 预期：429 错误时等待后重试
  - 验证：检查重试逻辑

- [ ] **测试 12**: 超时场景
  - 步骤：发送可能导致超时的请求
  - 预期：显示超时错误
  - 验证：检查超时处理

#### 4.1.5 上下文管理测试
- [ ] **测试 13**: 会话上下文
  - 步骤：
    1. 发送："我的名字是张三"
    2. 发送："我的名字是什么？"
  - 预期：第二次请求能记住上下文
  - 验证：检查响应是否包含"张三"

- [ ] **测试 14**: 历史消息限制
  - 步骤：发送超过 10 条消息
  - 预期：只保留最近 10 条消息
  - 验证：检查上下文是否正确限制

#### 4.1.6 参数配置测试
- [ ] **测试 15**: Temperature 参数
  - 步骤：使用不同的 temperature 值
  - 预期：输出创造性不同
  - 验证：检查输出差异

- [ ] **测试 16**: Max Tokens 参数
  - 步骤：设置较小的 max_tokens
  - 预期：输出长度受限
  - 验证：检查输出长度

---

### 4.2 性能测试

#### 4.2.1 响应时间测试
- [ ] **测试 17**: 非流式响应时间
  - 步骤：测量非流式请求的响应时间
  - 预期：响应时间 < 10 秒（取决于网络和 API）
  - 工具：使用 `time` 命令或代码计时

- [ ] **测试 18**: 流式响应首字时间
  - 步骤：测量流式响应第一个字符的时间
  - 预期：首字时间 < 2 秒
  - 验证：检查用户体验

#### 4.2.2 并发测试
- [ ] **测试 19**: 并发请求处理
  - 步骤：同时发送多个请求
  - 预期：所有请求都能正常处理
  - 验证：检查响应正确性

---

## 五、测试环境准备

### 5.1 测试环境要求

- Python 3.10+
- 虚拟环境已激活
- 测试依赖已安装：`pytest`, `pytest-asyncio`, `pytest-cov`
- DeepSeek API Key（用于集成测试和手动测试）

### 5.2 测试数据准备

#### 5.2.1 Mock 数据
- 使用 `unittest.mock` 创建 Mock 对象
- 所有 Mock 数据必须添加 `[MOCK]` 标识和打印

#### 5.2.2 测试用例数据
- 准备各种类型的测试消息（短文本、长文本、特殊字符等）
- 准备错误场景的测试数据

---

## 六、测试执行

### 6.1 运行单元测试

```bash
# 运行所有单元测试
pytest backend/ -v

# 运行特定模块测试
pytest backend/services/llm/tests/ -v
pytest backend/core/agent/tests/ -v
pytest backend/api/tests/ -v

# 运行带覆盖率的测试
pytest backend/ --cov=backend --cov-report=html

# 运行测试并显示打印输出（查看 [MOCK] 信息）
pytest backend/ -v -s
```

### 6.2 运行集成测试

```bash
# 运行集成测试
pytest tests/test_integration_deepseek.py -v

# 运行端到端测试
pytest tests/test_integration_deepseek.py::test_e2e_chat_flow -v -s
```

### 6.3 手动测试步骤

1. **准备环境**
   ```bash
   # 设置 API Key
   export DEEPSEEK_API_KEY=your_api_key
   
   # 启动后端
   python -m backend.main
   
   # 在另一个终端启动前端
   python -m frontend.main chat
   ```

2. **执行测试清单**
   - 按照 4.1 节的测试清单逐项测试
   - 记录测试结果
   - 发现问题及时记录

---

## 七、测试验收标准

### 7.1 单元测试标准
- [ ] 所有核心功能都有单元测试
- [ ] 测试覆盖率 > 80%
- [ ] 所有测试通过
- [ ] 所有 Mock 数据都有标识和打印

### 7.2 集成测试标准
- [ ] 端到端数据流测试通过
- [ ] 错误场景测试通过
- [ ] 上下文管理测试通过

### 7.3 手动测试标准
- [ ] 所有功能测试清单项通过
- [ ] 性能测试满足要求
- [ ] 用户体验良好

### 7.4 整体验收标准
- [ ] 所有测试通过
- [ ] 代码质量检查通过（lint、type check）
- [ ] 文档完整
- [ ] 无严重 bug

---

## 八、测试报告模板

### 8.1 测试执行报告

```markdown
# TODO-001 测试执行报告

## 测试环境
- Python 版本: 3.x.x
- 测试日期: YYYY-MM-DD
- 测试人员: XXX

## 测试结果

### 单元测试
- 总测试数: XX
- 通过: XX
- 失败: XX
- 覆盖率: XX%

### 集成测试
- 总测试数: XX
- 通过: XX
- 失败: XX

### 手动测试
- 总测试数: XX
- 通过: XX
- 失败: XX

## 发现的问题
1. [问题描述]
2. [问题描述]

## 结论
[通过/不通过]
```

---

## 九、持续测试

### 9.1 CI/CD 集成

- [ ] 配置 GitHub Actions 或类似 CI 工具
- [ ] 每次提交自动运行单元测试
- [ ] PR 合并前运行完整测试套件

### 9.2 测试维护

- [ ] 新功能添加时同步添加测试
- [ ] 定期更新测试用例
- [ ] 保持测试覆盖率 > 80%

---

## 十、相关文件

### 测试文件
- `backend/services/llm/tests/test_llm_service.py` - LLM 服务测试
- `backend/core/agent/tests/test_orchestrator.py` - Orchestrator 测试
- `backend/api/tests/test_routes.py` - API 路由测试
- `tests/test_integration_deepseek.py` - 集成测试（需创建）

### 文档文件
- `docs/todo/001-deepseek-integration.md` - 任务文档
- `docs/design/streaming-response.md` - 流式响应设计

---

**创建时间**: 2025-12-31  
**最后更新**: 2025-12-31








