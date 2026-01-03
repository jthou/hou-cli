# 测试脚本转换计划

## 当前测试脚本分析

### 1. `tests/test_context_manager_quick.py`
**类型**: 独立脚本测试  
**测试内容**: ContextManager 基础功能  
**使用 Mock**: ❌ 不需要（纯逻辑测试）

**转换建议**:
- ✅ **转化成单元测试** - 已有 `backend/core/agent/tests/test_context_manager.py`
- ❌ **不需要端到端测试** - 这是纯逻辑，不涉及外部依赖
- **行动**: 可以删除或保留作为快速验证脚本

---

### 2. `tests/test_e2e_chat.py`
**类型**: 独立脚本测试  
**测试内容**: 
- Orchestrator 上下文管理
- 流式响应上下文管理
- ContextManager 基础功能

**使用 Mock**: ✅ 是（Mock LLM Service）

**转换建议**:

#### 转化成单元测试 ✅
**目标文件**: `backend/core/agent/tests/test_orchestrator.py`  
**需要添加的测试用例**:
```python
@pytest.mark.asyncio
async def test_orchestrator_context_management():
    """测试 Orchestrator 的上下文管理"""
    # 测试第一轮对话后历史是否正确保存
    # 测试第二轮对话是否包含历史上下文

@pytest.mark.asyncio
async def test_orchestrator_stream_with_context():
    """测试流式响应的上下文管理"""
    # 测试流式响应是否正确保存到历史
```

**优势**:
- 使用 pytest 框架，更规范
- 可以集成到 CI/CD
- 测试报告更清晰

#### 转化成端到端测试 ✅
**目标文件**: `tests/test_e2e_chat_real.py` (新建)  
**需要测试的场景**:
```python
@pytest.mark.asyncio
async def test_e2e_chat_flow(backend_server):
    """测试真实的前后端交互"""
    # 1. 启动后端服务
    # 2. 发送 HTTP 请求到 /api/chat
    # 3. 验证响应格式
    # 4. 验证上下文是否正确传递

@pytest.mark.asyncio
async def test_e2e_stream_chat_flow(backend_server):
    """测试真实的流式对话"""
    # 1. 发送流式请求到 /api/chat/stream
    # 2. 验证 SSE 数据流
    # 3. 验证上下文管理
```

**优势**:
- 测试真实环境
- 验证完整数据流
- 发现集成问题

---

### 3. `tests/test_multi_turn_chat.py`
**类型**: 独立脚本测试  
**测试内容**: 多轮对话的上下文连贯性  
**使用 Mock**: ✅ 是（Mock LLM Service）

**转换建议**:

#### 转化成单元测试 ✅
**目标文件**: `backend/core/agent/tests/test_orchestrator.py`  
**需要添加的测试用例**:
```python
@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """测试多轮对话的上下文连贯性"""
    # 第一轮：用户说"我的名字是张三"
    # 第二轮：用户问"你还记得我的名字吗？"
    # 验证：LLM 请求中包含历史上下文
    # 验证：历史消息正确保存
```

**优势**:
- 测试逻辑清晰
- 可以快速运行
- 不依赖外部服务

#### 转化成端到端测试 ✅
**目标文件**: `tests/test_multi_turn_chat_real.py` (新建)  
**需要测试的场景**:
```python
@pytest.mark.asyncio
async def test_multi_turn_chat_real(backend_server):
    """测试真实的多轮对话场景"""
    # 1. 第一轮对话：发送"我的名字是张三"
    # 2. 第二轮对话：发送"你还记得我的名字吗？"
    # 3. 验证：后端返回包含"张三"
    # 4. 验证：上下文正确传递
```

**优势**:
- 测试真实 LLM 响应
- 验证完整用户体验
- 发现上下文传递问题

---

### 4. `tests/test_integration.py`
**类型**: pytest 集成测试  
**测试内容**: 后端健康检查和聊天 API  
**使用 Mock**: ❌ 否（真实后端服务）

**转换建议**:
- ✅ **已经是端到端测试** - 使用真实后端服务
- ✅ **需要扩展** - 添加更多端到端测试场景

**需要添加的测试用例**:
```python
@pytest.mark.asyncio
async def test_multi_turn_chat_integration(backend_server):
    """集成测试：多轮对话"""
    # 测试多轮对话的上下文管理

@pytest.mark.asyncio
async def test_stream_chat_integration(backend_server):
    """集成测试：流式对话"""
    # 测试流式响应的完整流程

@pytest.mark.asyncio
async def test_session_isolation(backend_server):
    """集成测试：会话隔离"""
    # 测试不同 session_id 的上下文隔离
```

---

## 转换优先级

### 高优先级（立即转换）

1. **`test_e2e_chat.py` → 单元测试**
   - 原因：已有 `test_orchestrator.py`，可以直接添加测试用例
   - 工作量：小（1-2 小时）

2. **`test_multi_turn_chat.py` → 单元测试**
   - 原因：测试逻辑清晰，适合单元测试
   - 工作量：小（1-2 小时）

### 中优先级（后续转换）

3. **`test_e2e_chat.py` → 端到端测试**
   - 原因：需要真实后端服务，测试完整数据流
   - 工作量：中（2-3 小时）

4. **`test_multi_turn_chat.py` → 端到端测试**
   - 原因：验证真实 LLM 响应的上下文管理
   - 工作量：中（2-3 小时）

### 低优先级（可选）

5. **`test_context_manager_quick.py` → 删除或保留**
   - 原因：已有完整的 pytest 单元测试
   - 工作量：小（删除或保留作为快速验证脚本）

---

## 转换后的测试结构

```
tests/
├── test_integration.py              # 现有：基础集成测试
├── test_e2e_chat_real.py           # 新建：真实端到端测试
├── test_multi_turn_chat_real.py    # 新建：真实多轮对话测试
└── test_context_manager_quick.py   # 可选：保留作为快速验证

backend/core/agent/tests/
├── test_context_manager.py         # 现有：单元测试
├── test_orchestrator.py            # 扩展：添加上下文管理测试
└── ...
```

---

## 转换步骤

### 步骤 1: 单元测试转换

1. 在 `backend/core/agent/tests/test_orchestrator.py` 中添加：
   - `test_orchestrator_context_management()` - 从 `test_e2e_chat.py` 转换
   - `test_orchestrator_stream_with_context()` - 从 `test_e2e_chat.py` 转换
   - `test_multi_turn_conversation()` - 从 `test_multi_turn_chat.py` 转换

2. 运行测试验证：
   ```bash
   pytest backend/core/agent/tests/test_orchestrator.py -v
   ```

### 步骤 2: 端到端测试创建

1. 创建 `tests/test_e2e_chat_real.py`：
   - 使用 `test_integration.py` 作为模板
   - 添加真实的前后端交互测试

2. 创建 `tests/test_multi_turn_chat_real.py`：
   - 测试真实的多轮对话场景
   - 验证 LLM 响应的上下文管理

3. 运行测试验证：
   ```bash
   pytest tests/test_e2e_chat_real.py -v
   pytest tests/test_multi_turn_chat_real.py -v
   ```

### 步骤 3: 清理旧脚本（可选）

1. 删除或重命名旧的独立脚本：
   - `test_e2e_chat.py` → 可以删除（已转换成单元测试）
   - `test_multi_turn_chat.py` → 可以删除（已转换成单元测试）
   - `test_context_manager_quick.py` → 可选保留

2. 更新 `test_all.sh`：
   - 改为运行 pytest 测试
   - 或保留作为快速验证脚本

---

## 测试覆盖对比

### 转换前
- ✅ 独立脚本测试（快速验证）
- ✅ Mock 数据测试（不依赖外部服务）
- ⚠️ 测试报告不统一
- ⚠️ 无法集成到 CI/CD

### 转换后
- ✅ pytest 单元测试（规范、可集成）
- ✅ pytest 端到端测试（真实环境）
- ✅ 统一的测试报告
- ✅ 可以集成到 CI/CD
- ✅ 测试覆盖率统计

---

## 总结

| 测试脚本 | 单元测试 | 端到端测试 | 优先级 |
|---------|---------|-----------|--------|
| `test_context_manager_quick.py` | ✅ 已有 | ❌ 不需要 | 低 |
| `test_e2e_chat.py` | ✅ 转换 | ✅ 转换 | 高 |
| `test_multi_turn_chat.py` | ✅ 转换 | ✅ 转换 | 高 |
| `test_integration.py` | ❌ 不需要 | ✅ 已有 | 中（扩展） |

**建议**: 先转换单元测试（高优先级），再创建端到端测试（中优先级）。


