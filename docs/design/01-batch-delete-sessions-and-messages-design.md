# 批量删除会话与历史消息 — 设计方案

**文档类型**：01X 系统组件 / 交互设计
**状态**：后端 API + 存储 + 前端四助手（通用/工作/写作/代码壳）已落地
**时间**：2026-03-21
**更新时间**：2026-03-21（前端批量 UI 与 `article_writing` 类型校验对齐说明）
**范围**：四个智能助手（通用对话、工作助手、写作助手、代码助手）共用同一套会话与消息存储模型，本方案一次设计、四处复用 UI 模式与 API。

---

## 1. 背景与目标

### 1.1 现状

- **单条消息**：已实现 `DELETE /api/sessions/{session_id}/messages/{message_id}`，各页通过 `useDeleteSessionMessage` 等调用。
- **单会话**：已实现 `DELETE /api/sessions/{session_id}`。
- **四助手**：`general_chat`、`work_assistant`、`article_writing`、`code_assistant`（代码助手复用通用对话壳，会话 `metadata.type` 区分）。

### 1.2 目标

| 能力 | 说明 |
|------|------|
| **批量删除历史消息** | 在同一会话内，多选若干条用户/助手消息，一次提交删除（减少重复点击与请求风暴）。 |
| **批量删除会话** | 在左侧会话列表多选若干 session，一次提交删除（或移入「回收站」若未来扩展）。 |

### 1.3 非目标（本阶段可不实现）

- 跨会话批量删消息（极少场景，复杂度高）。
- 服务端「回收站」与定时清理（可单列迭代）。
- IndexedDB 参考块随会话删除的联动：已采用第 7 节策略 **A**（`deleteReferenceBlocksForSessions`）。

---

## 2. 设计原则

1. **单一真相源**：消息与会话仍以服务端 `FileStorageBackend`（及未来可能的 DB 后端）为准；前端仅多选 + 调用批量 API + 刷新状态。
2. **与现网兼容**：不破坏现有单条 DELETE；批量接口为新增。
3. **可预期语义**：明确「全部成功 / 部分失败 / 全失败」的返回结构，便于 UI 与日志。
4. **写作助手特例**：`article_writing` 会话目录含 `current_article.md`、`mw_sources.json` 等；**删除整个会话**时行为与现单删会话一致（整目录清理策略保持不变）。**仅删消息**不删文章文件，除非产品明确要求「删消息同时清草稿」（本方案默认：**只删消息列表中的条目**）。

---

## 3. API 设计

### 3.1 为何部分接口用 POST

部分 HTTP 客户端/代理对 `DELETE` 带 body 支持不佳，故批量操作推荐 **POST + 明确 action 路径**（与业界常见做法一致）。

### 3.2 批量删除会话

**路径**：`POST /api/sessions/batch-delete`

**请求体**：

```json
{
  "session_ids": ["uuid-1", "uuid-2"],
  "expected_type": "work_assistant"
}
```

**校验**：

- `session_ids` 非空数组，长度上限 **50**（可配置），去重、去空白。
- 可选：body 字段 **`expected_type`**（与列表过滤 `type` 一致）。若传入则服务端仅允许删除类型匹配的会话，防止前端误传其它类型会话 ID（**推荐写作助手、工作助手等强校验**）。
- **`expected_type === "article_writing"` 特例**（与 `GET list_sessions` 过滤一致）：允许 `metadata.type` **缺失或空** 的会话通过校验（旧数据无 `type` 仍视为写作助手会话）；其它 `expected_type` 仍要求 `metadata.type === expected_type`。
- 传入 **`expected_type` 时**：每个 `session_id` 必须能通过 `get_session` 解析到索引中的会话，否则 **整单拒绝**（不执行删除），避免「无 metadata 可校验」的 id 混入批次（2026-03-21 审查闭环）。

**响应体（推荐：部分成功可报告）**：

```json
{
  "success": true,
  "deleted": ["uuid-1"],
  "failed": [
    { "session_id": "uuid-2", "error": "会话不存在" }
  ]
}
```

- 若业务要求 **原子性**（要么全删要么全不删）：可实现为数据库事务；当前文件存储可实现为「先校验全部存在再逐个删」，任一失败则 **不执行任何删除** 并返回 `success: false`。**建议第一版采用「尽力删除 + 返回 deleted/failed」**，UX 更清晰。

**实现要点**：

- 复用现有 `ContextManager.delete_session(session_id)` 循环调用；注意锁与 `sessions.json` 并发写入（与现 `_sessions_lock` 策略一致）。
- 若当前选中会话在被删列表中，前端需在成功后清空选中并 `sessionStorage` 键。

### 3.3 批量删除消息（单会话内）

**路径**：`POST /api/sessions/{session_id}/messages/batch-delete`

**请求体**：

```json
{
  "message_ids": ["mid-1", "mid-2", "mid-3"]
}
```

**校验**：

- `message_ids` 非空，上限 **100**（可配置），去重。
- `session_id` 路径参数与会话存在性校验。

**响应体**：

```json
{
  "success": true,
  "deleted": ["mid-1", "mid-2"],
  "failed": [
    { "message_id": "mid-3", "error": "消息不存在" }
  ]
}
```

**存储层建议**：

- `FileStorageBackend` 增加 `delete_messages(session_id, message_ids: List[str]) -> Dict` 或返回 `(deleted, failed)`：
  - **一次读盘** → 过滤掉所有命中 id → **一次写回**（json 或 jsonl 与现 `delete_message` 分支逻辑一致）。
  - 避免 N 次打开文件。
- `message_id` 比对统一使用与单删相同的规范化（如 `_normalize_message_id`）。
- **并发（2026-03-21）**：同一会话的 `save_message` / `get_messages`（含写回补全 id）/ `delete_message` / `delete_messages` / `clear_session` / `delete_session` 在文件后端侧对 **该 session 的消息文件** 使用 **同一把 `threading.Lock`** 串行化读-改-写，避免多请求互相覆盖（单进程内有效；多进程部署需文件锁或外部队列）。

**并发**：同一会话若与用户正在发送流式请求并发，可能出现「删完后又写入新消息」——与单条删除一致，属可接受竞态；可选后续对会话加短期锁（超出本方案范围）。

---

## 4. 前端交互设计（四助手统一模式）

### 4.1 会话列表：批量删 session

1. **入口**：左侧会话列表顶部或底部增加「多选」开关，或长按/复选框模式（桌面 Web 推荐每行 checkbox）。
2. **操作条**：选中 ≥1 项后显示浮动条：`已选 N 个` + `批量删除` + `取消全选`。
3. **确认**：Modal / `toast.confirm`，文案明确不可恢复（写作助手可强调「会话内文章草稿一并删除」若整会话删除）。
4. **调用**：`POST /api/sessions/batch-delete`，根据响应更新列表；若有 `failed`，toast 列出前几条错误摘要。
5. **类型隔离**：各页面仅展示本 `sessionType` 的会话，请求可带 `expected_type` 与列表 ID 双保险。

**代码助手**：与通用对话共用 `GeneralChat`，一套组件即可。

### 4.2 对话区：批量删消息

1. **入口**：对话区域工具栏「选择消息」或每条气泡左侧出现 checkbox（进入编辑模式后显示）。
2. **规则**：
   - 允许混选 user/assistant；删除语义为「从持久化历史中移除这些条」，不自动删「成对」的另一条（避免误删链路复杂）；可在 UI 上提示「删除后上下文可能不连续」。
   - 或产品可选：**选中 user 时提示是否同时删除紧邻的下一条 assistant**（第二迭代）。
3. **流式中**：loading 时禁用批量删除或禁用未落库条目的勾选（与单条删除「无 message_id 不可删」一致）。
4. **调用**：`POST .../messages/batch-delete`，成功后 `setMessages` 过滤掉 `deleted` 中的 id，或对失败 id 保持并提示。

### 4.3 可复用抽象

- `useBatchDeleteSessions({ sessionType, loadSessions, selectedSessionId, setSelectedSessionId, storageKey })`
- `useBatchDeleteMessages({ sessionId, setMessages, toast })`

与现有 `useDeleteSessionMessage` 并列，减少四处复制。

---

## 5. 安全与权限

- 当前应用为 **本地单用户**，无多租户 ACL；仍应对 `session_ids` 做 **类型与存在性** 校验，避免脚本恶意遍历 ID。
- 上限条数防止超大 body DoS。

---

## 6. 测试与验收

| 用例 | 预期 |
|------|------|
| 批量删 3 个会话，2 成功 1 不存在 | `deleted.length === 2`，`failed` 含 1 条 |
| 批量删消息，含无效 id | 有效删除，无效进入 `failed` |
| 仅 jsonl 会话 | 与单删一致，batch 写回 jsonl |
| 写作助手删会话 | 目录与现 `delete_session` 行为一致 |
| 前端全选后取消 | 无请求 |

---

## 7. 与 IndexedDB 的关系

- **聊天历史**不在 IndexedDB；批量删消息/会话 **不依赖** IndexedDB。
- **参考块**存于 IndexedDB（`articleWritingIndexedDB.js`），按 `sessionId` + `sessionType` 索引。**已采用策略 A**：批量删会话成功后，前端对成功删除的 id 调用 `deleteReferenceBlocksForSessions`（失败仅 `console.warn`，不阻断列表刷新）。

---

## 8. 实施顺序建议

1. **后端**：`FileStorageBackend.delete_messages` + 路由 `batch-delete`（消息）与 `sessions/batch-delete`（会话） - **【已完成】**。
2. **集成测试**：真实临时目录跑文件存储 - **【已完成】**。
3. **前端**：会话列表批量删除 + 消息多选批量删除 - **【已完成】**（`useBatchDeleteSessions` / `useBatchDeleteMessages` + Vitest）。
4. **四页接入**：`GeneralChat`（含代码助手）、`WorkAssistant`、`ArticleWriting` - **【已完成】**。

---

## 9. 附录：与现有路由对照

| 能力 | 现有 | 新增 |
|------|------|------|
| 删一条消息 | `DELETE /api/sessions/{id}/messages/{mid}` | `POST /api/sessions/{id}/messages/batch-delete` |
| 删一个会话 | `DELETE /api/sessions/{id}` | `POST /api/sessions/batch-delete` |

保持旧接口长期可用，文档与 OpenAPI/审计表同步更新。

## 10. 实现状态更新

**后端实现状态**（截至 2026-03-21）：
- ✅ `FileStorageBackend.delete_messages` - 已实现
- ✅ `FileStorageBackend.delete_sessions` - 已实现
- ✅ `ContextManager.delete_messages` - 已实现
- ✅ `ContextManager.delete_sessions` - 已实现
- ✅ `POST /api/sessions/{session_id}/messages/batch-delete` - 已实现
- ✅ `POST /api/sessions/batch-delete` - 已实现
- ✅ `expected_type` 参数校验 - 已实现
- ✅ 批量数量限制（消息100条，会话50个）- 已实现
- ✅ 部分成功/失败响应结构 - 已实现
- ✅ 相关单元测试与集成测试 - 已实现

**前端实现状态**（截至 2026-03-21）：
- ✅ 会话列表多选 + 底部操作条（全选/清空/批量删除）
- ✅ 对话区「选择消息」+ 有 `message_id` 的条目可勾选；流式 `loading` 时禁用批量删消息
- ✅ `useBatchDeleteSessions` / `useBatchDeleteMessages` + 单测
- ✅ `GeneralChat`、`WorkAssistant`、`ArticleWriting` 接入（代码助手走 `GeneralChat` 壳）
