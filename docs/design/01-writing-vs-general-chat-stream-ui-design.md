# 写作助手 vs 通用对话：中间区（过程/参考/上下文）设计指引

**时间**：2026-03-13  
**理由**：两页能力边界不同，但用户心智需要「可预期、可解释」；避免重复造轮子或长期分叉。  
**方法**：分层原则 + 统一协议 + 按 Agent 差异化展示。

---

## 1. 设计目标

1. **可解释**：用户能回答「模型此刻在干什么、用了什么上文、参考从哪来」。
2. **不抢正文**：写作场景以**可编辑成稿**为主，过程信息默认**次要、可折叠**。
3. **协议统一、表现分化**：SSE/编排侧尽量同一套事件；前端按 `context_type` 决定默认展开与文案。
4. **成本可控**：写作默认**无工具链**；额外 LLM（如意图解读）归入「可选增强」，须有开关与失败降级策略（见既有 `ENABLE_WRITING_INTENT_INJECTION`）。

---

## 2. 分层模型（推荐）

| 层级 | 含义 | 通用对话 | 写作助手 |
|------|------|----------|----------|
| **L1 正文流** | 用户主要阅读区 | 助手 Markdown | 助手 Markdown（建议与「状态前缀」分离展示，保持现状 `stripAgentStatusPrefix`） |
| **L2 过程轨** | 工具、子 Agent、意图块、编排步骤 | 工具卡片 +（已有）编排 trace | 默认仅 **编排 trace / 意图注入摘要**（无工具时工具卡隐藏） |
| **L3 上下文轨** | 「用了哪些历史/参考/草稿」 | `ContextSelectionPanel` + `__CTX_META__` | **条件展示**：仅当后端对该轮实际下发 `__CTX_META__` 时显示；无则不占位 |
| **L4 资料轨** | 用户显式提供的材料 | 参考块 + 会话设置（身份/工具） | 参考块 + 写作画像 + **右侧草稿**（草稿属「成稿资产」，非中间气泡） |

**原则**：L3 不是「通用对话专属」，而是 **「本轮请求是否做了混合上下文选择」** 的反映；写作若未来接入混合历史或检索片段，应复用同一组件与协议，避免再写一套 UI。

---

## 3. 更合理的具体取舍

### 3.1 中间区：写作是否要有 Context 面板？

- **合理做法**：**有协议就显示，没协议不假装有**。  
  - 实现上：写作页与通用对话**共用** `parseContextMetaChunk` + `ContextSelectionPanel`（或抽一层 `StreamContextRail`）。  
  - 当 `article_writing` 当前仍不传 `__CTX_META__` 时，面板不出现，**不增加视觉噪音**。  
- **不合理做法**：为写作单独做一套「假上下文说明」或与后端不一致的文案。

### 3.2 「思考过程」文案与编排前言

- **合理做法**：  
  - 将 `执行 xxx 代理...`、STREAM_AGENT_PREAMBLE、ORCH_TRACE 统一归为 **L2 过程轨**，默认折叠或单行，不与正文混在一个 Markdown 里（写作侧已部分做到）。  
  - 通用对话可选：对同类前缀做与写作一致的剥离，避免正文里出现「执行…代理」污染复制与朗读。  
- **不合理做法**：各页各写一套正则；应在 `streamChunkFilters` 或共享 hook 里 **单一实现**。

### 3.3 参考资料与「进模型」的一致性

- **合理做法**：  
  - 用户可见的「参考块 / 画像」与后端注入顺序在文档中写清（契约层已有 `article_writing_message_contract`、参考块工具函数）。  
  - 可选增强（意图解读块）在设计上明确属于 **L2 或 L3 的摘要**，而不是让用户误以为是用户自己写的指令。  
- **不合理做法**：前端展示「参考」与后端实际 `user_prompt` 结构长期不一致。

### 3.4 工具与技能

- **合理做法**：  
  - 写作默认无工具；若未来开放「检索后再写」等能力，应 **显式开关 + 过程轨展示工具结果**，并更新 CHAT/ARTICLE 系统提示边界。  
  - 通用对话继续 **技能门控 + 工具子集**（会话 metadata），与中间区工具卡一致。  

---

## 4. 后端契约建议（与前端对齐）

1. **`__CTX_META__`**：只要任意 Agent 做了「非 trivial 的上下文裁剪/混合」，就应下发，**同一 JSON 形状**，由前端统一渲染。  
2. **`__ORCH_TRACE__`**：verbosity 由 env / 请求 context 控制；写作与通用对话 **同一解析路径**。  
3. **写作 `user_prompt` 结构顺序**：在设计文档中保持唯一事实源（草稿前缀 → 画像 → 用户 task → 系统检出 → 可选意图块）；意图解读实现见 `backend/core/agent/intent_interpreter.py` 与 `ENABLE_WRITING_INTENT_INJECTION`（`env.example`）。

---

## 5. 落地阶段（建议）

| 阶段 | 内容 |
|------|------|
| **P0** | ✅ 已实现：`shouldAppendStreamingPlainText`（`utils/streamSseContent.js`）+ `parseContextMetaChunk`（`utils/streamContextMeta.js`）；`ArticleWriting.jsx`、`GeneralChat.jsx`、`WorkAssistant.jsx` 共用；写作页条件渲染 `ContextSelectionPanel`；`isOrchestratorControlChunk` 含 `__CTX_META__:` 兜底。 |
| **P1** | ✅ 已实现：`stripAgentStatusPrefix`（`utils/streamUi.js`），`GeneralChat`、`ArticleWriting`、`WorkAssistant` 历史气泡与流式区共用。 |
| **P2** | ✅ 已实现：`article_writing` 流式在拼完 `user_prompt` 后下发 `strategy=article_writing` 的 `__CTX_META__`（草稿锚点、**参考块**（task 含 `【参考` 或标准参考引言）、画像、系统检出、本轮指令摘要；**不**表示注入了会话聊天历史）。开关 `ENABLE_ARTICLE_WRITING_CTX_META`（默认 true）。实现：`article_writing_context_meta.py`（含 `task_contains_reference_blocks`）+ `orchestrator.py`；编排回归见 `test_orchestrator_context_type_routing.py::test_article_writing_stream_yields_ctx_meta`（需在项目 venv 下跑，依赖 httpx 等）。 |

**单测**：`frontend/react-app/src/utils/streamSseContent.test.js`、`streamChunkFilters.test.js`、`src/components/ContextSelectionPanel.test.jsx`（`article_writing` 策略）。

**后端快速回归**（需项目 `.venv` 或 `venv`）：`make test-stream-ctx`（仅跑 `test_article_writing_context_meta` + `test_orchestrator_context_type_routing`）。

**CLI**：`scripts/test_article_writing_opening_rewrite.py --check-ctx-meta`；无参考块场景加 `--check-ctx-meta-allow-no-reference`；`--verbose` 时额外打印解析后的 JSON。

---

## 6. 非目标（避免过度设计）

- 不要求写作与通用对话 **中间栏布局像素级一致**（写作有右侧成稿，信息架构本就不同）。  
- 不默认给写作加 **完整工具栏**（除非产品明确「写作也要搜/write」）。  
- 不把 **意图解读的完整 JSON** 默认暴露给最终用户（开发者 trace 即可）。

---

## 7. 相关文档与代码

- 编排与 context_type：`backend/core/agent/orchestrator.py`（`general_chat` vs `article_writing` 分支）。  
- 通用对话上下文面板：`frontend/react-app/src/pages/GeneralChat.jsx`、`ContextSelectionPanel.jsx`。  
- 写作流式 UI：`frontend/react-app/src/pages/ArticleWriting.jsx`（`stripAgentStatusPrefix`、参考块/画像）。  
- 三级记忆与混合历史：`docs/design/01-three-level-memory-and-context-design.md`。
