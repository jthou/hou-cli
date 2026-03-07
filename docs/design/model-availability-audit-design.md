# 模型可用性审计设计

## 背景

当模型 API 余额耗尽、免费额度用尽（如 `AllocationQuota.FreeTierOnly`）、限流（429）或权限不足（403）时，用户需要快速了解哪些模型可用、哪些不可用，以便切换模型或前往管理台充值/调整设置。

## 目标

- 对**每个模型**主动发起一次简单请求（如 "hello"）
- 有回馈 → 显示**可用**
- 报错 → 显示**具体错误信息**

## 模型列表来源

- **目标**：列出 `.env` 中**所有**模型，**含注释中**提到的（示例、可选值、默认值等）
- **来源**：解析 `.env` 文件内容，提取：
  1. **配置行**：`*_MODEL=value` → 提取 value
  2. **注释行**：匹配 `KEY=model`、`示例：KEY=model`、`可选值：model1, model2`、`默认值：model` 等模式

**解析规则**：
- 读取项目根目录 `.env` 文件（若不存在则读 `env.example` 作为模板）
- 配置行：`^([A-Z_]+_MODEL)\s*=\s*(.+)$`，取 value 并 strip
- 注释行：匹配以下模式提取模型名
  - `(?:示例|可选值|默认值)[：:]\s*(?:[A-Z_]+_MODEL=)?([a-zA-Z0-9\-\._]+)`
  - `-\s+([a-zA-Z0-9\-\._]+)：`（列表项）
  - `\*\s+"([^"]+)"`（引号内模型名）
  - `([a-zA-Z0-9\-\._]+),\s*`（逗号分隔的模型列表）
- 过滤：排除明显非模型（如 `deepseek`、`bailian`、`true`、`false`、纯数字等）
- 去重：按模型值去重

**已知的模型相关 key**（`MODEL_CONFIG_KEYS` 提供 label）：
- `CHAT_MODEL`、`CODE_MODEL`、`REASONING_MODEL`
- `DEEPSEEK_MODEL`、`BAILIAN_MODEL`、`TURBOGATEWAY_MODEL`
- `BROWSER_TOOL_VISION_MODEL`、`BROWSER_TOOL_REASONING_MODEL`、`BROWSER_TOOL_CHAT_MODEL`

**备选方案**：若解析注释过于复杂，可合并 `model_registry.py` 中的全量模型列表（DEEPSEEK_MODELS ∪ OPENAI_MODELS ∪ ANTHROPIC_MODELS ∪ GOOGLE_MODELS ∪ PERPLEXITY_MODELS ∪ BAILIAN_MODELS）与 `.env` 中 `*_MODEL` 的实际值，作为「所有已知模型」列表。该列表已覆盖 env.example 注释中提到的绝大多数模型。

**API**：`GET /api/settings/model-availability-audit/models`
- 返回：`{ "models": [...], "unique_models": [...] }`
- `models`：每项含 `key`、`label`、`model`、`source`（`"config"` | `"comment"`）
- `unique_models`：去重后的模型名列表，用于探测

## 设计方案

### 主动探测：对每个模型发 "hello"

**流程**：
1. 获取用户可选模型列表（与模型选择下拉一致）
2. 对每个模型发送一条极简消息，例如 `[{"role":"user","content":"hello"}]`
3. 若收到正常回复 → 标记为**可用**
4. 若抛出异常 → 标记为**不可用**，并展示错误信息（如 403、FreeTierOnly、余额不足等）

**页面**：
- 路由：`/settings/model-availability-audit`（或并入模型审计页）
- 展示：表格，列：模型名、状态（可用/不可用）、错误信息（失败时）
- 操作：**检测全部** 按钮，点击后依次探测所有模型，实时更新状态

**后端 API**：

```
GET /api/settings/model-availability-audit/models
  - 返回 .env 中所有 *_MODEL 变量及其值，按模型去重

POST /api/settings/model-availability-audit/probe
Body: 空 或 { "models": ["deepseek-chat", "gpt-4o-mini", ...] }
  - 不传或空：从 GET /models 的 unique_models 取列表
  - 传 models：按指定列表探测

响应：一次性返回
{
  "success": true,
  "results": [
    { "model": "deepseek-chat", "ok": true },
    { "model": "gpt-4o-mini", "ok": false, "error": "Error code: 403 - {'error': {'message': 'The free tier...', 'type': 'AllocationQuota.FreeTierOnly'}}" }
  ]
}
```

**实现要点**：
- 复用现有 `LLMService` 或底层 chat 接口，传入 `model` 覆盖
- 请求内容尽量短，减少 token 消耗（"hello" 即可）
- 超时设短（如 15 秒），避免长时间阻塞
- 探测结果**不写入** llm_audit，避免污染审计日志（或可选写入并标记为 probe）

---

## 数据流

```
前端：加载页面
    ↓ GET /api/settings/model-availability-audit/models
后端：解析 .env（或 env.example），提取配置行与注释中的模型，返回 models + unique_models

前端：点击「检测全部」
    ↓ POST /api/settings/model-availability-audit/probe（或带 models 参数）
后端：遍历 unique_models，对每个模型调用 chat([{role:user, content:"hello"}])
    ↓ 成功 → { model, ok: true }
    ↓ 失败 → { model, ok: false, error: str(e) }
前端：表格展示每个模型的状态与错误信息
```

---

## 文件变更清单

| 文件 | 变更 |
|-----|------|
| `backend/api/` | 新增 model_availability_routes：`GET /models`（解析 .env 含注释提取所有模型）、`POST /probe` |
| `backend/utils/` 或 `backend/services/llm/` | 新增 `parse_env_models()`：读取 .env，解析配置行与注释，提取模型列表 |
| `backend/services/llm/` | 封装 `probe_model(model) -> {ok, error?}` |
| `frontend/.../SettingsModelAvailabilityAudit.jsx` | 新建页面：从 GET /models 加载模型列表 + 检测按钮 + 结果表格 |
| `App.jsx` / `Sidebar.jsx` | 注册 `/settings/model-availability-audit` 路由 |
