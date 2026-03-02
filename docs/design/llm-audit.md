# LLM 对话审计设计

## 目的

对**每一次**送入 LLM 的输入与 LLM 的输出做审计记录，便于排查问题、复现对话与合规留痕。

## 审计与写文章会话的区别

- **LLM 对话审计**：**全局、按时间顺序**记录所有 LLM 调用。不区分 session、不区分会话类型（写文章、任务、通用对话等），只要是 `LLMService.chat()` / `stream_chat()` 的调用都会按发生时间写入同一审计存储。用 `audit_id` 关联单次调用的请求与响应。
- **写文章会话**：按 **session** 维度的业务数据（消息列表、current_article、参考页等），存于 contexts 下的各 session 目录。与审计是两套数据：审计是「每次 LLM 调用的时间线」，写文章是「每个会话的内容」。

审计记录里的 `session_id`（若有）仅为**可选元数据**，表示该次调用所属会话，便于按会话筛选日志，**不会**把审计按 session 或类型拆分存储。

## 存储方式：SQLite 数据库

- **为何用数据库**：与项目内 sessions、task_queue 等一致，便于备份、索引与查询；分页、按日期/时间区间筛选由 SQL 完成，无需扫文件。
- **位置**：`{应用数据目录}/databases/llm_audit.db`（通过 `StorageManager.get_sqlite_path("llm_audit.db")`，与其它 DB 同目录）。
- **表结构**：`llm_audit (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, record TEXT NOT NULL)`，`record` 为单条审计的完整 JSON；`ts` 为 UTC ISO8601，用于按日/区间查询与排序。
- **索引**：`ts` 建索引，便于按时间范围查询与排序。

**旧版 JSONL 迁移**：若存在旧目录 `{应用数据目录}/llm_audit/` 及其中的 `llm_audit_*.jsonl` 文件，在首次调用 `list_audit_dates()` 时会自动执行 `migrate_legacy_jsonl_to_db()`：将全部 JSONL 记录导入数据库，然后删除已迁移的 JSONL 文件及空目录。

## 记录类型（direction）

| direction         | 含义           | 何时写入 |
|------------------|----------------|----------|
| `request`        | 送入 LLM 的输入 | 每次调用 `chat` / `stream_chat` 前 |
| `response`       | LLM 正常输出   | 调用成功返回后（含流式收齐后的完整内容） |
| `response_error` | 调用异常       | 超时、HTTP 错误、网络错误或其它异常时 |

## 单条记录结构

每条 JSON 行包含：

- `ts`: UTC 时间，ISO8601 格式，如 `2025-02-27T12:00:00.000000Z`
- `direction`: `request` | `response` | `response_error`
- `model`: 本次使用的模型名
- `payload`: 具体内容摘要（见下）
- 其它来自 `meta` 的字段（如 `session_id`, `audit_id`, `usage`, `stream_interrupted` 等）

### payload 约定

- **request**  
  - `message_count`: 消息条数  
  - `messages`: 数组，每项含 `role`, `content_length`, `content_preview`（长内容会截断，见 `llm_audit.py` 中的长度限制）

- **response**  
  - `type`: `text` | `tool_calls` | `null` | `other`  
  - 文本：`content_length`, `content_preview`（过长截断）  
  - 工具调用：`count`, `names`

- **response_error**  
  - `error`: 异常信息字符串  
  - `error_type`: 异常类型名  
  - 流式出错时可能有：`partial_length`, `partial_preview`

## 请求与响应关联（audit_id）

同一次 LLM 调用（一次 `chat()` 或一次 `stream_chat()`）会先写一条 `request`，再写一条 `response` 或 `response_error`。通过 **audit_id** 关联：

- 在写入 `request` 时生成 `audit_id`（16 位 hex），并写入该条记录的 `meta`
- 同一次调用的 `response` / `response_error` 使用相同 `audit_id` 写入 `meta`

在日志中按 `audit_id` 筛选即可得到「一次请求 + 其对应结果」。

## 流式调用的特殊标记

- **正常结束**：流式收齐后写一条 `response`，与普通 `chat` 的 `response` 结构一致，带同一 `audit_id`。
- **用户中断（KeyboardInterrupt）**：写一条 `response`，`meta` 中带 `stream_interrupted: true`，`payload` 为已产生的局部内容摘要。
- **流式迭代中异常**：写一条 `response_error`，`payload` 中可含 `partial_length`、`partial_preview`，便于排查中断时的部分输出。

## 内容长度限制

- 单条消息预览：`MAX_MESSAGE_PREVIEW_LEN`（默认 8000 字符）
- 响应/内容预览：`MAX_CONTENT_LEN`（默认 50000 字符）  
超出部分截断并注明「已截断」，避免审计文件过大。

## 实现位置

- 审计逻辑：`backend/services/llm/llm_audit.py`  
  - `create_audit_id()`  
  - `append_audit(direction, model, payload, meta=None)`（写入 SQLite）
  - `list_audit_dates()`、`read_audit_records()`、`read_audit_records_range()`（从 DB 分页查询）
- 调用点：`backend/services/llm/llm_service.py`  
  - `LLMService.chat()`：请求前写 request，成功写 response，异常写 response_error，均带 `audit_id`  
  - `LLMService.stream_chat()`：同上，并处理流式中断/异常时的局部响应与 `stream_interrupted`
- 谁触发都会记：所有调用 `LLMService.chat()` / `stream_chat()` 的路径（Orchestrator 对话、写文章、技能、评估等）都会写入同一审计库，无类型过滤。若调用方有 session（如 Orchestrator 带 session_id），则把 `session_id` 放入 `audit_meta`，审计记录中可带 `session_id` 便于按会话检索，但**不**改变「全局按时间序」的存储方式。

## 使用方式

- 审计写入失败仅打日志，不抛异常，不影响主流程。
- 数据库不可用时（如 `get_storage_manager()` 或建表失败），不写记录，仅 warning 日志。
- **关闭审计**：设置环境变量 `LLM_AUDIT_DISABLED=1`（或 `true`/`yes`），则不再写入任何审计记录，适用于生产环境或磁盘敏感场景。

查询：通过设置页「LLM 对话审计」按日期或时间区间、分页查看；或直接查 SQLite（按 `audit_id`、`session_id` 等筛选 `record` JSON）。
