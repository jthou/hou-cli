# 对话 Session 设计评审与改进方案

**阅读说明**：第二节为评审时归纳的不完善之处，其中多项已在第六节「实现状态」中标注为已解决；第一节概览已按当前实现做了同步（含 list 参数、stream 支持、PATCH 等）。

## 一、当前设计概览

### 1.1 存储

- **后端**：`ContextManager` + `FileStorageBackend`
  - **存储根目录**：`get_app_data_dir() / "contexts"`（如 macOS：`~/Library/Application Support/hou-cli/contexts`）
  - 会话列表：`sessions.json`（session_id、created_at、updated_at、metadata）
  - 消息：`<session_id>/messages.json`
  - 写文章草稿：`<session_id>/current_article.md`（仅写文章会话使用）
- **Session 模型**：session_id、created_at、updated_at、metadata（dict，可存 type、后续可扩展 title 等）

### 1.2 API

- `POST /api/sessions`：创建会话，可选 body `{ "metadata": { "type": "article_writing" } }`；无 body 时 metadata 为空。
- `GET /api/sessions/list?limit=&type=&sort=&order=&offset=`：列出会话；`type=article_writing` 时仅返回 metadata.type 匹配的会话；`sort=updated_at|created_at`、`order=asc|desc`、`offset` 支持排序与分页；返回项含 `title`（来自 metadata.title，空则 fallback preview）。返回 `{ "sessions": [ { session_id, title, preview, ... }, ... ], "error"?: string }`。
- `GET /api/sessions/{id}`：会话详情 + 消息列表；404 或失败时返回 `success: false`。
- `GET /api/sessions/search?keyword=&limit=`：按关键词搜索会话（preview、session_id、metadata 匹配）。
- `GET /api/chat/article?session_id=`：当前文章草稿；无 session_id 或失败时返回 `article: null`。
- `POST /api/chat`：发送消息，支持 session_id、current_article、context_type（建新会话时写入 metadata.type）；返回 response、article（有 session_id 时）。
- `POST /api/chat/stream`：流式发送，支持 session_id、current_article、context_type，流式分支会注入并保存 current_article。
- `PATCH /api/sessions/{id}`：更新会话，支持 `{ "title": "...", "metadata": { ... } }`。
- `DELETE /api/sessions/{id}`、`POST /api/sessions/{id}/clear`：删除会话 / 清空消息（clear 会删掉整个 session_dir，**含 current_article**）。

### 1.3 写文章页

- 左侧：写文章会话列表（仅 type=article_writing），新建会话用 POST /api/sessions + metadata
- 中间：选中会话的对话 + 输入框
- 右侧：当前会话的 current_article 预览；每次发送带 current_article，后端注入上下文并持久化

### 1.4 会话创建来源

- **写文章页**：必须「新建会话」或选已有会话，再发消息 → 会话带 metadata.type=article_writing；发消息时可带 context_type=article_writing 以保持类型。
- **Orchestrator（无 session_id 时）**：若请求带 context_type（如写文章入口），则 `create_session(metadata={ type })`，新会话会出现在写文章列表；否则无 type。

---

## 二、不完善之处与风险

### 2.1 会话无独立「标题」，列表可读性差（已改进：见第六节）

- **现状**：列表展示依赖 `get_session_preview` 的 preview（首条用户消息截断）。
- **问题**：首条是「帮我写一篇文章」「你好」等通用语时，多个会话在列表中难以区分；新会话无消息时 preview 为空，显示为「新会话」或空白。
- **影响**：会话一多，左侧列表辨识度低。

### 2.2 会话类型只靠创建入口，无事后标记（已改进：见第六节）

- **现状**：写文章会话依赖「从写文章页通过 POST /api/sessions 带 metadata」创建；若未来有入口先发消息再建会话（不传 session_id），Orchestrator 会无参 create_session，该会话没有 type，不会出现在写文章列表。
- **风险**：若以后支持「先聊再选会话类型」或通用对话页误用，会产生「无类型」会话，与写文章列表过滤逻辑不一致。

### 2.3 列表无删除/清空入口（已改进：见第六节）

- **现状**：后端有 DELETE、clear 接口，写文章页左侧列表没有「删除会话」「清空消息」等操作。
- **问题**：用户无法在写文章场景下清理废弃会话，只能依赖后端或手动删文件。

### 2.4 clear_session 与 current_article 的语义（已明确）

- **现状**：`clear_session` 已用 `shutil.rmtree(session_dir)`，会删掉 messages 和 current_article.md，行为一致。
- **建议**：在文档或接口说明中明确「清空会话 = 删除该会话下所有消息与当前文章草稿」，避免误以为只清消息。

### 2.5 列表排序与分页（已改进：见第六节）

- **现状**：仅按 updated_at 倒序，limit 由前端写死（如 50）。
- **问题**：无法按创建时间、标题等排序；会话非常多时没有分页或游标，前端一次拉全量。

### 2.6 多端 / 多 Tab 一致性

- **现状**：无乐观锁、无推送；同一 session 在多个 Tab 或设备编辑时，后写覆盖先写，无冲突检测。
- **影响**：当前单用户、单页使用可接受；若以后多端同时编辑同一会话，需要「最后写入胜出」或版本/冲突策略并在文档中说明。

### 2.7 预览生成策略单一（已改进：见第六节）

- **现状**：preview 仅「首条用户消息」截断。
- **问题**：首条过短或为寒暄时，列表项信息量不足；没有用首条助手回复或摘要增强可读性。

### 2.8 Session 元数据不可变（已改进：见第六节）

- **现状**：创建时写入 metadata 后，无 API 更新 Session（如改 title、改 type）。
- **问题**：无法重命名会话、无法把误建的「普通会话」改为写文章会话。

### 2.9 无会话过期与归档

- **现状**：会话永久保留，仅受磁盘与 list limit 限制。
- **问题**：长期使用会积累大量会话，列表噪音大；没有「归档」或「过期」策略。

### 2.10 流式 chat 未支持 current_article（已改进：见第六节）

- **现状**：`POST /api/chat/stream` 只传 session_id，不接收、不保存 current_article，也不在上下文中注入。
- **影响**：写文章页若改用流式，右侧文章无法参与上下文，需继续使用非流式 POST /api/chat。

### 2.11 错误与边界未统一约定

- **现状**：各接口错误时有的返回 `success: false` + error，有的返回 `status: "error"` + error；list 失败时返回 `{ sessions: [], error }`。
- **建议**：在文档或接口规范中统一错误格式（如 HTTP 4xx/5xx 与 body 结构），便于前端统一处理。

### 2.12 安全与多用户（可选）

- **现状**：无鉴权，会话按进程/存储目录全局可见；未按用户隔离。
- **影响**：当前单机、单用户可接受；若以后多用户，需在存储或 API 层按 user_id 隔离 session。

---

## 三、改进方案（按优先级）

### P0：必做 / 体验刚需

1. **会话标题（title）**
   - **模型**：Session 使用 `metadata.title` 存可编辑标题（或单独字段，视存储兼容性）。
   - **API**：  
     - `GET /api/sessions/list` 返回项中带 `title`（来自 metadata.title，空则 fallback preview）。  
     - `PATCH /api/sessions/{id}` 或 `PUT /api/sessions/{id}` 支持 `{ "title": "..." }` 更新 metadata.title。
   - **前端**：列表优先展示 title，空则展示 preview；支持「重命名」或首条消息发送后自动用首句前 N 字写入 title（可选）。

2. **写文章列表的删除/清空**
   - **前端**：在左侧列表项上增加操作（如菜单或图标）：  
     - 「删除会话」：调用 `DELETE /api/sessions/{id}`，成功后从列表移除并清空选中。  
     - 「清空消息」：调用 `POST /api/sessions/{id}/clear`，成功后刷新当前会话的消息与文章（当前会话若为选中项则重载）。
   - **后端**：在文档中明确 clear 会同时删除 current_article（已实现：clear 会删除 session_dir，含 current_article.md）。

### P1：建议做

3. **Chat 创建会话时支持传入 context 的 type**
   - **API**：`POST /api/chat` 支持可选 `context_type` 或 body 中 `metadata: { type: "article_writing" }`；若本次请求没有 session_id 且需要创建新会话，则用该 type 调用 `create_session(metadata={ "type": context_type })`。
   - **作用**：未来若有「先发一句再建会话」的流程，仍可正确标记写文章会话，与写文章列表过滤一致。

4. **列表排序与分页**
   - **API**：`GET /api/sessions/list` 增加 `sort=updated_at|created_at`（及可选 `order=asc|desc`）、`offset`、`limit`（上限如 100）。
   - **前端**：写文章页可先用默认 sort=updated_at&order=desc；需要时再暴露「按创建时间」或分页。

5. **Preview 增强**
   - **策略**：  
     - 若有 `metadata.title` 优先作为列表展示文案（不写入 preview 字段也可，仅展示用）。  
     - preview 字段：无 title 时用「首条用户消息」；若首条过短（如 <15 字），可再 fallback 到首条 assistant 前 100 字或保持现状，避免列表项全为「你好」类短句。

### P2：可后续迭代

6. **PATCH /api/sessions/{id}**
   - 支持更新 `metadata`（含 title、type 等），便于重命名、改类型、加标签。

7. **会话过期 / 归档**
   - 策略示例：超过 N 天未更新的会话在 list 中过滤掉，或标记为「归档」仅归档页展示；或仅在前端做「隐藏旧会话」不落库。可先定策略再动存储。

8. **多端一致性说明**
   - 在文档中写明：当前为「最后写入胜出」，无冲突合并；多 Tab 建议通过刷新或重选会话获取最新状态。

9. **流式 chat 支持 current_article（可选）**
   - 若写文章页希望改为流式输出，需在 `POST /api/chat/stream` 中支持接收、保存 current_article，并在 orchestrator 流式分支中注入当前文章到上下文；响应结束时可返回最新 article（或通过 SSE 事件单独推送）。

---

## 四、推荐落地顺序

1. **短期**：实现 P0（会话 title + 列表删除/清空），并补充「clear 会删 current_article」的接口/文档说明。  
2. **中期**：实现 P1（chat 建会话带 type、list 排序与分页、preview 增强）。  
3. **长期**：按需做 P2（PATCH 更新会话、过期/归档、多端说明）。

---

## 五、与公众号草稿的对照

| 维度           | 公众号草稿                     | 写文章 Session                 |
|----------------|--------------------------------|---------------------------------|
| 列表数据源     | 公众号 API 草稿列表            | GET /api/sessions/list?type=   |
| 新建           | 新建草稿（创建任务）           | POST /api/sessions + metadata  |
| 选中后主内容   | 草稿详情 + 编辑                | 对话 + 输入框                  |
| 右侧           | 任务列表                       | 文章预览                        |
| 删除/清空      | 依赖公众号或任务               | 已实现：列表项删除/清空入口    |

保持「左侧列表 + 中间主操作 + 右侧辅助」的布局一致，差异仅在数据源与操作语义；Session 侧补足 title 与删除/清空后，体验可与公众号草稿页对齐。

---

## 六、实现状态（与文档同步）

| 项 | 状态 | 说明 |
|----|------|------|
| P0 会话标题（title） | ✅ | metadata.title、PATCH 更新、list 返回 title、前端重命名与首条消息自动设标题 |
| P0 删除/清空入口 | ✅ | 前端列表项删除/清空操作，后端 DELETE、clear；文档明确 clear 含 current_article |
| P1 context_type | ✅ | POST /api/chat 支持 context_type，建新会话时 create_session(metadata={ type }) |
| P1 列表排序与分页 | ✅ | list 支持 sort、order、offset、limit；前端写文章页支持排序 |
| P1 Preview 增强 | ✅ | get_session_preview 首条过短时 fallback 首条 assistant 前 100 字；list 返回 title |
| P2 PATCH 更新会话 | ✅ | PATCH /api/sessions/{id} 支持 title、metadata |
| P2 流式 current_article | ✅ | POST /api/chat/stream 支持 current_article、context_type，流式分支注入并保存 |
| 会话过期/归档、多端一致性 | 未做 | 见 P2 可后续迭代 |

**关联**：LLM 对话审计（见 [llm-audit.md](./llm-audit.md)）会记录每次请求/响应，审计记录中可带 `session_id`，便于按会话排查问题。

---

## 七、Review 完善性检查清单

评审时可用以下项自检文档与实现是否一致、是否有遗漏：

- [x] **存储**：路径、文件结构、Session/Message 模型与代码一致
- [x] **API 列表**：所有 session/chat 相关接口已列出（list、get、create、delete、clear、search、article、chat、chat/stream、PATCH）
- [x] **行为约定**：clear 含 current_article、list 的 type 过滤已写明；stream 已支持 current_article
- [x] **不完善项**：标题、类型标记、删除/清空入口、排序分页、preview、元数据可更新等已实现；过期归档、多端、错误格式、安全为后续
- [x] **改进方案**：P0/P1 及部分 P2 已落地，落地顺序与文档一致
- [x] **对照**：与公众号草稿的差异与对齐点已说明

---

## 八、相关文档

- [写文章 MediaWiki 参考源](./article-writing-mediawiki-sources.md)：会话参考文章（多页面）的配置与注入
- [写文章预览内容设计](./article-writing-preview-content.md)：右侧预览与 current_article 的更新策略
- [LLM 对话审计](./llm-audit.md)：请求/响应审计与 audit_id、session_id 关联
