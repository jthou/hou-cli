# 流式 Agent 身份前缀与编排摘要

**时间**：2026-03-21  
**关联**：[01-orchestrator-intent-driven-refactor-design.md](./01-orchestrator-intent-driven-refactor-design.md)（编排 trace）、审计页 LLM 请求展示

---

## 1. 审计里「请求 / 响应」在写作场景下的逻辑关系

以你提供的片段为例（`article_writing`、单次 `stream_chat` / 同构调用）：

| 部分 | 含义 |
|------|------|
| **请求 · system** | Orchestrator 为 **写作助手** 注入的 **系统提示**：`get_article_writing_system_prompt(...)`，内含人设、写作偏好、输出规则、禁止工具等。 |
| **请求 · user** | 本轮 **用户消息**：常由前端拼成「作者画像 / 写文约束 / 参考块 + 用户提问」。模型 **不读历史多轮**（设计如此），信息都在这一条 user 里。 |
| **模型（如 qwen3-max）** | 页选或编排选出的 **同一模型**，既吃 system 也吃 user。 |
| **响应** | 模型在 **仅依据上述 system+user** 下的续写；若 user 里尚未给出「具体题目/参考正文」，模型会 **合规则地索要** 参考列表与本次写作要求——这不是第二个 Agent，而是 **同一写作助手角色** 在按提示词办事。 |

**结论**：这不是「多 Agent 接力」，而是 **UnifiedOrchestrator → 选模 → 单次（流式）生成**；审计里看到的是 **一条对话链路** 的 system/user 与模型回复。

若需「谁在编排」的可视化，见 **ORCH_TRACE**（`ORCH_TRACE_VERBOSITY`）与本文 **STREAM_AGENT_PREAMBLE**。

---

## 2. 流式正文前缀（产品要求）

在 **不默认开启** 的前提下，支持：

- **`【我是xxxAgent】`**：标明当前对外输出所代表的角色（写作助手 / 工作助手 / 通用对话 / 技能执行等）。
- **`full` 模式**：多一行 **`【我是编排协调Agent】`** + 路由摘要（`context_type`、是否跳过技能预匹配、模型名、工具数/直出等）。

实现：`backend/core/agent/stream_agent_preamble.py`，由主 `stream_process` 在 **技能成功输出**、**带工具流式**、**无工具直出** 三种路径的 **首段正文前** 插入。

### 配置

| 方式 | 说明 |
|------|------|
| 环境变量 `STREAM_AGENT_PREAMBLE`（或 `STREAM_AGENT_PREAMBLE_MODE`） | `off`（默认）\|`identity`\|`full`；`on`/`true`/`1` 视为 `identity` |
| `context["stream_agent_preamble"]` | 同上字符串，**优先于**环境变量 |

---

## 3. 与 ORCH_TRACE 的区别

| 机制 | 形态 | 默认 |
|------|------|------|
| `__ORCH_TRACE__` | 结构化 JSON 行，便于前端单独面板解析 | 关 |
| `STREAM_AGENT_PREAMBLE` | **进入正文的纯文本前缀**，用户直接可见 | 关 |

二者可同时开；前缀更适合「对话气泡里一眼看出谁在说话」。
