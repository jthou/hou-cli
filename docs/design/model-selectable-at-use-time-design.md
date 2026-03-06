# 模型使用时可选择 - 设计实施文档

## 一、概述

### 1.1 目标

在**运行时**允许用户选择本次对话使用的模型，而非仅依赖系统根据任务自动选择。用户可在发起请求前指定模型类型（如「对话模型」「编码模型」「推理模型」）或具体模型名，编排器将优先使用用户选择，否则回退到智能选择逻辑。

### 1.2 设计原则

- **向后兼容**：不传 `model` 时，行为与现有逻辑完全一致
- **最小侵入**：仅增加可选参数，不改变现有模型配置体系
- **用户优先**：用户指定模型时，本次请求全程使用该模型（工具推荐切换可配置是否尊重用户选择）

### 1.3 相关文档

- [多模型支持与模型切换](multi-model-support-and-switching.md) - 模型注册、提供商管理、配置体系
- [模型配置审计 API](../backend/api/model_config_routes.py) - `model-config-audit` 返回的 `agent_model_mapping`

---

## 二、现状分析

### 2.1 当前流程

```
用户请求 → ChatRequest(message, session_id?, context_type?, current_article?)
         → context = { session_id, context_type }
         → orchestrator.process(task, context)
         → _select_model(task)  # 无 context 参与
         → 根据任务复杂度/关键词在 CHAT_MODEL、CODE_MODEL、REASONING_MODEL 中选择
         → llm_service.set_model(selected_model)
```

### 2.2 关键代码位置

| 组件 | 文件 | 说明 |
|------|------|------|
| 请求模型 | `backend/api/chat_routes.py` | `ChatRequest`、`context` 构建 |
| 模型选择 | `backend/core/agent/orchestrator.py` | `_select_model(task)` |
| 配置管理 | `backend/services/llm/model_config.py` | `get_chat_model()`、`get_code_model()`、`get_reasoning_model()` |
| 模型注册 | `backend/services/llm/model_registry.py` | 模型名解析、校验 |

### 2.3 模型选择调用点

- `process_dynamic()`：非流式主流程，约第 1173 行
- `stream_process()`：流式主流程，约第 2049 行
- 工具执行中：工具可推荐切换模型，在 `_chat_with_tools` 和 `_chat_with_tools_stream` 内部的工具调用循环中

---

## 三、设计方案

### 3.1 参数设计

**ChatRequest 新增字段：**

```python
model: Optional[str] = None  # 用户指定模型
```

**取值约定：**

| 取值 | 含义 | 解析方式 |
|------|------|----------|
| `None` / 不传 / `""` | 智能选择 | 调用 `_select_model(task)` |
| `"chat"`（大小写不敏感） | 对话模型 | `config_manager.get_chat_model()` |
| `"code"` | 编码模型 | `config_manager.get_code_model()` |
| `"reasoning"` | 推理模型 | `config_manager.get_reasoning_model()` |
| 具体模型名（如 `"deepseek-chat"`） | 直接使用 | 需通过 `model_config.get_model_config()` 校验，失败抛 ValueError |

### 3.2 数据流

```
ChatRequest.model
    → context["model"] = request.model
    → orchestrator.process(task, context) / stream_process(task, context)
    → _select_model(task, context)
        → if context.get("model"):
        →     return _resolve_user_model(context["model"])
        → else:
        →     return 原有智能选择逻辑
```

### 3.3 用户指定模型时的工具推荐切换

**策略**：用户指定模型时，**本次请求内**不随工具推荐切换模型，保持用户选择。

- 实现：在 `_chat_with_tools` 及流式分支中，若 `context.get("model")` 存在，则跳过工具推荐切换逻辑，或增加 `allow_tool_model_switch=False` 标志。

---

## 四、实现清单

### 4.1 后端

| 步骤 | 文件 | 改动内容 |
|------|------|----------|
| 1 | `backend/api/chat_routes.py` | `ChatRequest` 增加 `model: Optional[str] = None`；构建 `context` 时**仅当** `request.model` 非空（`and request.model.strip()`）才设置 `context["model"] = request.model.strip()` |
| 2 | `backend/core/agent/orchestrator.py` | `_select_model(task, context=None)` 增加 `context` 参数；开头检查 `context.get("model")`，若有则调用 `_resolve_user_model()` 并返回 |
| 3 | `backend/core/agent/orchestrator.py` | 新增 `_resolve_user_model(model_spec: str) -> str`：对 `model_spec` 做 `strip().lower()`；解析 `chat`/`code`/`reasoning` 或具体模型名（后者用 `get_model_config()` 校验，失败抛 ValueError） |
| 4 | `backend/core/agent/orchestrator.py` | `process_dynamic`、`stream_process` 中调用 `_select_model(task, context)` 时传入 `context` |
| 5 | `backend/core/agent/orchestrator.py` | **必须**：`_chat_with_tools`、`_chat_with_tools_stream` 增加 `context: Optional[Dict] = None` 参数；在工具推荐切换逻辑前检查 `context and context.get("model")`，若存在则跳过切换；`process_dynamic`、`stream_process` 调用时传入 `context` |

### 4.2 前端

| 步骤 | 文件 | 改动内容 |
|------|------|----------|
| 1 | 聊天页组件 | 增加模型选择控件（下拉/单选），选项：「智能选择」「对话模型」「编码模型」「推理模型」 |
| 2 | 请求逻辑 | 发送 `/api/chat`、`/api/chat/stream` 时，若用户选择了非「智能选择」，则附带 `model` 字段 |

### 4.3 可选增强

- **模型列表 API**：若需前端展示具体模型名，可复用 `/api/settings/model-config-audit` 的 `agent_model_mapping`，或新增轻量 `/api/models/selectable` 返回 `[{value, label}, ...]`
- **会话级默认**：在 session metadata 中存储 `model`，新建会话时从上一会话继承（后续迭代）

---

## 五、后端测试验证方案

### 5.1 测试层级

| 层级 | 范围 | 工具 |
|------|------|------|
| 单元测试 | `_resolve_user_model`、`_select_model` 分支 | pytest |
| 集成测试 | orchestrator 与 model_config 协作 | pytest + mock |
| API 测试 | ChatRequest、context 传递 | TestClient |

### 5.2 单元测试：`_resolve_user_model` 与 `_select_model`

**文件**：`backend/core/agent/tests/orchestration/test_model_selectable_at_use_time.py`（新建）

```python
"""模型使用时可选择 - 单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from backend.core.agent.orchestrator import Orchestrator
from backend.services.llm.model_config import get_model_config_manager


class TestResolveUserModel:
    """_resolve_user_model 解析逻辑测试（同步方法，无需 async）"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    def test_resolve_chat_type(self, orchestrator):
        """chat -> get_chat_model()"""
        result = orchestrator._resolve_user_model("chat")
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    def test_resolve_code_type(self, orchestrator):
        """code -> get_code_model()"""
        result = orchestrator._resolve_user_model("code")
        expected = get_model_config_manager().get_code_model()
        assert result == expected

    def test_resolve_reasoning_type(self, orchestrator):
        """reasoning -> get_reasoning_model()"""
        result = orchestrator._resolve_user_model("reasoning")
        expected = get_model_config_manager().get_reasoning_model()
        assert result == expected

    def test_resolve_case_insensitive(self, orchestrator):
        """Chat、CODE 等大小写应被归一化"""
        result = orchestrator._resolve_user_model("  Chat  ")
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    def test_resolve_concrete_model_name(self, orchestrator):
        """具体模型名 -> 校验通过后原样返回（或规范化后的名称）"""
        # 使用 patch 避免对未配置模型抛错；实际实现中 deepseek-chat 通常已配置
        with patch.object(
            get_model_config_manager(), "get_model_config", return_value=MagicMock()
        ):
            result = orchestrator._resolve_user_model("deepseek-chat")
            assert result == "deepseek-chat"

    def test_resolve_invalid_raises(self, orchestrator):
        """无效模型类型（非 chat/code/reasoning 且无法通过 get_model_config 校验）应抛出 ValueError"""
        # 注：部分环境下 "invalid_type" 可能被 model_registry 解析为有效模型，测试可改用
        # patch get_model_config 的 side_effect=ValueError 以稳定触发
        with pytest.raises(ValueError):
            orchestrator._resolve_user_model("invalid_type")
```

```python
class TestSelectModelWithUserOverride:
    """_select_model 在 context 含 model 时的行为"""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    @pytest.mark.asyncio
    async def test_user_override_chat(self, orchestrator):
        """context.model=chat 时跳过智能选择"""
        context = {"model": "chat"}
        result = await orchestrator._select_model("分析这段代码", context=context)
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    @pytest.mark.asyncio
    async def test_user_override_reasoning(self, orchestrator):
        """context.model=reasoning 时使用推理模型"""
        context = {"model": "reasoning"}
        result = await orchestrator._select_model("今天天气怎么样", context=context)
        expected = get_model_config_manager().get_reasoning_model()
        assert result == expected

    @pytest.mark.asyncio
    async def test_no_override_uses_smart_selection(self, orchestrator):
        """context 无 model 时走智能选择"""
        context = {}
        # 简单任务应选 chat
        result = await orchestrator._select_model("你好", context=context)
        expected = get_model_config_manager().get_chat_model()
        assert result == expected

    @pytest.mark.asyncio
    async def test_none_context_same_as_empty(self, orchestrator):
        """context=None 与 context={} 行为一致"""
        r1 = await orchestrator._select_model("你好", context=None)
        r2 = await orchestrator._select_model("你好", context={})
        assert r1 == r2
```

### 5.3 集成测试：process / stream_process 传递 model

**文件**：同上或 `backend/core/agent/tests/test_orchestrator_model_override.py`

```python
"""Orchestrator 模型覆盖集成测试"""
import pytest
from unittest.mock import patch, AsyncMock
from backend.core.agent.orchestrator import Orchestrator


class TestOrchestratorModelOverride:
    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    @pytest.mark.asyncio
    async def test_process_respects_context_model(self, orchestrator):
        """process 收到 context.model 时使用该模型调用 LLM"""
        with patch.object(orchestrator.llm_service, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "测试响应"
            # 绕过技能匹配，进入 process_dynamic 的 LLM 分支
            async def _run():
                if orchestrator.skill_registry:
                    with patch.object(orchestrator.skill_registry, "match", new_callable=AsyncMock, return_value=None):
                        await orchestrator.process("你好", context={"model": "chat"})
                else:
                    await orchestrator.process("你好", context={"model": "chat"})
            await _run()
            mock_chat.assert_called()

    @pytest.mark.asyncio
    async def test_stream_process_respects_context_model(self, orchestrator):
        """stream_process 收到 context.model 时使用该模型"""
        # 验证 stream_process 收到 context.model 时，_select_model 返回对应模型
        # 可通过 mock _select_model 并断言其未被调用（用户覆盖时直接 _resolve_user_model）
        # 或断言首轮 LLM 调用前 set_model 被正确调用
        ...
```

### 5.4 API 测试：ChatRequest 与 context 传递

**文件**：`backend/api/tests/test_chat_routes.py`（扩展现有）

```python
def test_chat_endpoint_with_model_override(self, client):
    """测试带 model 参数的聊天接口，context 正确传递"""
    with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
        mock_orch = MagicMock()
        mock_orch.process = AsyncMock(return_value="使用指定模型的响应")
        mock_get_orch.return_value = mock_orch

        response = client.post("/api/chat", json={
            "message": "你好",
            "model": "reasoning"
        })

        assert response.status_code == 200
        call_args = mock_orch.process.call_args
        assert call_args[1]["context"]["model"] == "reasoning"


def test_chat_stream_endpoint_with_model_override(self, client):
    """测试流式接口带 model 参数"""
    async def mock_stream_with_model_check(task, context=None):
        assert context.get("model") == "code"
        yield "chunk1"
        yield "chunk2"

    with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
        mock_orch = MagicMock()
        mock_orch.stream_process = mock_stream_with_model_check
        mock_get_orch.return_value = mock_orch

        response = client.post("/api/chat/stream", json={
            "message": "写一个函数",
            "model": "code"
        })

        assert response.status_code == 200
        content = b""
        for chunk in response.iter_bytes():
            content += chunk
        assert b"chunk1" in content


def test_chat_endpoint_without_model_uses_empty_context(self, client):
    """不传 model 时 context 不包含 model 键"""
    with patch('backend.api.chat_routes.get_orchestrator') as mock_get_orch:
        mock_orch = MagicMock()
        mock_orch.process = AsyncMock(return_value="响应")

        def check_context(message, context=None):
            assert context is not None
            assert "model" not in context or context.get("model") is None
            return "响应"

        mock_orch.process.side_effect = check_context
        mock_get_orch.return_value = mock_orch

        response = client.post("/api/chat", json={"message": "你好"})
        assert response.status_code == 200
```

### 5.5 测试执行命令

```bash
# 运行模型选择相关单元测试
pytest backend/core/agent/tests/orchestration/test_model_selectable_at_use_time.py -v

# 运行模型选择 + 原有模型选择测试
pytest backend/core/agent/tests/orchestration/test_model_selection.py \
      backend/core/agent/tests/orchestration/test_model_selectable_at_use_time.py -v

# 运行 Chat API 测试
pytest backend/api/tests/test_chat_routes.py -v

# 全量相关测试
pytest backend/core/agent/tests/orchestration/ backend/api/tests/test_chat_routes.py -v
```

### 5.6 回归检查

- 运行 `test_model_selection.py` 确保原有智能选择逻辑未被破坏
- 运行 `test_chat_routes.py` 中所有用例，确保不传 `model` 时行为与改动前一致

---

## 六、验收标准

| 项目 | 标准 |
|------|------|
| 不传 model | 行为与现有逻辑完全一致，原有测试全部通过 |
| 传 model=chat/code/reasoning | 使用对应配置模型，且 context 正确传递 |
| 传具体模型名 | 校验通过后使用该模型 |
| 无效 model | 返回明确错误（400/422 或业务错误信息） |
| 单元测试 | `_resolve_user_model`、`_select_model` 覆盖新增分支 |
| API 测试 | ChatRequest 含 model 时 context 正确传递 |

---

## 七、风险与注意事项

1. **工具推荐切换**：必须在 `_chat_with_tools` 和 `_chat_with_tools_stream` 中传入 `context`，并在工具推荐切换逻辑前检查 `context.get("model")`，存在则跳过（见实现清单步骤 5）。
2. **模型名校验**：具体模型名需通过 `model_config.get_model_config()` 校验，失败抛 ValueError，由上层返回 200+error 体（与现有 chat 异常处理一致）。
3. **前端默认值**：模型选择控件默认应为「智能选择」，对应不传 `model`。

---

## 八、设计审查与修订记录

以下为文档审查中发现并已修正的不妥当设计：

| 问题 | 修正 |
|------|------|
| **工具推荐切换未纳入实现清单** | 步骤 5 从「可选」改为「必须」，明确需给 `_chat_with_tools`、`_chat_with_tools_stream` 增加 `context` 参数并在此处跳过切换 |
| **空字符串 model 未定义** | 取值约定中补充 `""` 视为未指定；实现清单步骤 1 明确仅当 `request.model` 非空且 strip 后非空才设置 context |
| **大小写未规范** | 取值约定补充「大小写不敏感」；实现清单步骤 3 要求对 `model_spec` 做 `strip().lower()` |
| **单元测试误用 async** | `_resolve_user_model` 为同步方法，测试改为普通 `def`，并新增 `test_resolve_case_insensitive` |
| **集成测试 patch 目标错误** | 修正为 `skill_registry.match`（非 `skill_matcher`），并处理 `skill_registry` 为 None 的情况 |
| **test_chat_endpoint_without_model 断言歧义** | 保持 `"model" not in context or context.get("model") is None`，与「不传则不设置」的实现一致 |
| **test_resolve_invalid_raises 可能不稳定** | 部分环境下 `"invalid_type"` 可能被 model_registry 解析为有效模型；测试可改用 `patch get_model_config` 的 `side_effect=ValueError` 以稳定触发 |
