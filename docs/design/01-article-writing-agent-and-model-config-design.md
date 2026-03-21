# 写作助手：Agent、大模型与可配置性设计

**文档类型**：01X 系统组件 / 配置与路由  
**状态**：现状说明；§6.1 执行顺序修复 **已于 2026-03-21 落地**；其余为可选提案  
**时间**：2026-03-21  
**范围**：前端「写作助手」页（`context_type=article_writing`）所触发的编排、技能、Agent 与 LLM 调用链；**不含**通用对话、工作助手。

---

## 1. 目标与术语

| 术语 | 含义 |
|------|------|
| **写作助手** | React `ArticleWriting.jsx`，请求中带 `context_type: article_writing`。 |
| **Orchestrator** | `backend/core/agent/orchestrator.py` 中的编排器：选技能、调 LLM、流式输出；**不是**一个独立注册的 Agent 类，但承担「路由 + 模型切换」。 |
| **写作类技能** | 仅在 `article_writing` 白名单内匹配的技能（见 §2）。 |
| **ArticleWritingAgent** | `ArticleWritingAgent`（继承 `BlogWritingAgent`），在**部分技能**内部用于多步写文章（大纲/正文 JSON 等）。 |

---

## 2. 写作助手用到的 Agent / 技能 / 直接 LLM

### 2.1 工具（Tools）

`article_writing` 在 `agent_tools_registry.py` 中 **不配备任何工具**（`AGENT_TOOLS["article_writing"] = []`）。写作助手对话路径 **不向 LLM 传入 function calling 工具列表**（与通用对话不同）。

### 2.2 技能白名单（Skills）

配置位置：`backend/core/agent/agent_tools_registry.py` → `AGENT_SKILLS["article_writing"]`：

| 技能名 | 说明 | 内部实现要点 |
|--------|------|----------------|
| `article_outline` | 生成文章大纲 | 技能内直接使用 `context["llm_service"].chat(...)`，**不**经过 `ArticleWritingAgent`。 |
| `article_write` | 撰写正文 | 通过 `get_article_writing_agent(...)` 使用 **`ArticleWritingAgent`**（继承 `BlogWritingAgent`），内部多步调用同一 `llm_service`。 |
| `article_style_apply` | 按画像润色 | 使用 `ArticleWritingAgent` 或同类写文章链路（以代码为准）。 |
| `writing_profile_summary` | 从用户粘贴的文章总结写作画像 | 技能内 **`LLMService.chat`**，**不**使用 `ArticleWritingAgent`。 |

### 2.3 与「写作画像」相关、但不在写作助手对话里的调用

| 能力 | 入口 | LLM 使用方式 |
|------|------|----------------|
| **根据高分章节更新画像** | `POST /api/settings/writing-profile/learn-from-ratings` | `writing_profile_routes.py` 内 **`LLMService()` 默认实例**，与 Orchestrator 当前 `model` **无联动**。 |

---

## 3. 大模型实际从哪里来？

### 3.1 共享的 `LLMService` 实例

`Orchestrator` 构造时创建 **`self.llm_service = LLMService()`**（默认 `LLM_PROVIDER` + 各提供商的 `*_MODEL` 环境变量，见 `llm_service.py`）。  
技能执行时 `context["llm_service"]` **即该实例**。

### 3.2 写作助手主对话（流式 `/api/chat/stream`）

1. 前端 `ArticleWriting` 通过 **`ModelSelector`** 选择模型，请求体带 **`model`**。  
2. `chat_routes` 将 `model` 放入 `context["model"]`。  
3. 在 **`stream_process` 中**，若未命中技能，则在调用 `stream_chat` **之前**执行 `_select_model`：  
   - 若 `context["model"]` 有值，优先解析为用户指定模型（含 `chat` / `code` / `reasoning` 别名）；  
   - 否则走智能选择（复杂度、`CHAT_MODEL` / `CODE_MODEL` / `REASONING_MODEL` 等）。  
4. **`self.llm_service.set_model(selected_model)`** 后，流式对话使用该模型。

**结论**：主对话使用的模型 = **用户所选** 或 **智能选择结果**，对应环境变量中的 **`CHAT_MODEL` / `CODE_MODEL` / `REASONING_MODEL`**（经 `ModelConfigManager` 解析）。

### 3.3 技能路径（含「总结画像」）— 执行顺序（已修复）

**历史问题**：在旧实现中，技能在 **`_select_model` + `set_model` 之前**执行，技能内看到的是 **`LLMService` 构造默认模型**，与页选模型不一致。

**当前行为（2026-03-21）**：在 `UnifiedOrchestrator.stream_process` 中，于 **`skill_registry.match` 之后、`matched_skill.execute` 之前** 调用 **`_select_model` + `set_model`**；未命中技能的主路径 **不再第二次**调用 `_select_model`。技能分支正常结束前 **`reset_model()`**，与主路径一致。同步地，`process()` 在技能前统一 `_select_model`，技能成功返回前 `reset_model()`；`_intelligent_orchestration` 内不再重复 `_select_model`（由 `process()` 入口保证已选模）。

`learn-from-ratings`（`writing_profile_routes`）仍为独立 `LLMService()`，与对话所选模型无联动（见 §4）。

### 3.4 默认线路与环境变量（全局）

| 变量 | 作用 |
|------|------|
| `LLM_PROVIDER` | `deepseek` / `bailian` / `theturbogateway`（默认 deepseek） |
| `DEEPSEEK_MODEL` / `BAILIAN_MODEL` / `TURBOGATEWAY_MODEL` | 未显式传 `model` 构造 `LLMService` 时的默认模型 id |
| `CHAT_MODEL` / `CODE_MODEL` / `REASONING_MODEL` | `_select_model` 与别名 `chat`/`code`/`reasoning` 解析用 |

API Key、Base URL 由 `model_config.py` 中提供商表映射（如 `DEEPSEEK_API_KEY`）。

---

## 4. 是否可配置？今天怎么配？

| 能力 | 今天能否配 | 怎么配 |
|------|------------|--------|
| 写作助手 **主对话** 模型 | ✅ | 页内模型选择器 → `context.model`；或依赖服务端智能选择 + `CHAT_MODEL` 等。 |
| **技能**（含总结画像）在流式中的模型 | ✅ 与主对话一致 | 流式：`stream_process` 在 execute 前 **`_select_model`**（含 `context["model"]`）。仍受全局 `LLM_PROVIDER` / Key 约束。 |
| **learn-from-ratings** | ⚠️ 仅全局默认 | `LLMService()` 新实例，同全局 `LLM_PROVIDER` + `*_MODEL`。 |

**流式「总结画像」**已与页选模型对齐（§3.3、§6.1）。**若要让「根据高分章节更新画像」与某指定模型一致**：须改 `learn-from-ratings` 路由（共用 Orchestrator 或显式 `set_model` / 环境变量），见 §6.2 提案。

---

## 5. 配置页面放哪里更合适？（提案）

### 5.1 原则

- **模型与密钥**：偏「基础设施」，宜集中在 **设置 → 模型/服务商** 一类入口，与现有 **模型配置审计**（`SettingsModelConfigAudit`）心智一致。  
- **写作业务偏好**（画像、范文）：已在 **设置 → 写作画像**，不宜把大量 API 密钥塞进去。  
- **写作助手专属默认模型**：介于两者之间，建议 **单独小节** 可折叠，避免与「全站 CHAT_MODEL」混淆。

### 5.2 推荐信息架构

1. **首选（推荐）**  
   - 在 **设置** 下增加或扩展 **「模型与 API」** 页（若已有则追加区块）：  
     - **全局**：`CHAT_MODEL` / `CODE_MODEL` / `REASONING_MODEL`、智能选择开关（与现有后端 env 对齐的可视化或说明）。  
     - **写作助手**：  
       - 「对话默认模型」：与当前页内选择器关系写清楚（是否覆盖、是否仅默认）。  
       - 「技能专用模型（可选）」：`writing_profile_summary` / `article_outline` / `article_write` 共用或分项（见 §6 实现选项）。  

2. **次选（轻量）**  
   - 在 **写作画像** 页增加 Tab **「模型」**：仅配置与写作相关的 LLM（总结画像、learn-from-ratings）。  
   - 缺点：用户找「API Key」仍要去别处，容易分裂。

3. **不推荐**  
   - 仅放在 `ArticleWriting` 主界面深处：高级用户难以发现，且与全局 Key 重复配置易冲突。

### 5.3 与现有路由的对应关系（前端）

- 写作画像：`/settings/writing-profile`  
- 模型审计：`/settings/model-config-audit`（名称以 `App.jsx` 为准）  
- 提案新增区块可挂在 **模型审计同组侧边栏**，或 **写作画像子 Tab**，二选一为主、另一处放简短链接跳转。

---

## 6. 实现可配置时的后端方向（提案）

1. **执行顺序修复（高优先级）** — **已完成**  
   - 实现位置：`backend/core/agent/orchestrator.py` 的 `stream_process`（match 之后、技能 execute 之前）、`process()`（同上）；回归：`backend/core/agent/tests/test_orchestrator_stream_skill_model.py`。

2. **可选：写作专用模型环境变量**  
   - 例如 `ARTICLE_WRITING_SKILL_MODEL`：仅当设置时，技能路径强制 `set_model` 到该值；否则回退到用户所选 / `CHAT_MODEL`。  
   - `learn-from-ratings` 可读取同一变量，避免与对话完全脱节。

3. **持久化**  
   - 若做 UI 配置页，需 **后端存储**（如扩展 `settings` API 或复用现有 model 配置存储），启动时或请求时同步到 `LLMService`；**不得**仅前端 localStorage 决定计费模型（除非明确为「仅本机覆盖」产品）。

---

## 7. 验收与文档维护

- 自动化：`pytest backend/core/agent/tests/test_orchestrator_stream_skill_model.py`。  
- 手工：在写作助手触发 `writing_profile_summary`，确认审计日志 / 调试 SSE 中 **模型选择** 与页选一致。  
- 本文档应在以下变更时更新：  
  - `AGENT_SKILLS["article_writing"]` 增减技能；  
  - `ArticleWritingAgent` 调用链变化；  
  - `_select_model` 或技能执行顺序调整。

---

## 8. 附录：相关代码索引

| 模块 | 路径 |
|------|------|
| 技能白名单 | `backend/core/agent/agent_tools_registry.py` |
| 流式编排与技能顺序 | `backend/core/agent/orchestrator.py`（`stream_process`） |
| 模型选择 | `Orchestrator._select_model` |
| 写作画像总结技能 | `backend/core/agent/skills/writing_profile_summary/skill.py` |
| 写文章 Agent | `backend/core/agent/agents/article_writing_agent.py` |
| 高分学习画像 API | `backend/api/writing_profile_routes.py`（`learn_from_ratings`） |
| 全局模型名配置 | `backend/services/llm/model_config.py`（`CHAT_MODEL` 等） |
| 流式请求传 model | `backend/api/chat_routes.py` |

---

**小结**：写作助手 **主对话与流式技能**（含总结画像）在 **`stream_process` 内共用同一轮 `_select_model` 结果**（含页选 `context["model"]`）。**设置页「根据高分章节更新画像」** 仍为独立默认线路。配置页建议仍以 **设置 → 模型与 API** 为主；可选 **`ARTICLE_WRITING_SKILL_MODEL`** 等见 §6.2。
