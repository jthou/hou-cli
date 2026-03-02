# LLM 对话审计设计

## 目的

对每次送入 LLM 的输入与 LLM 的输出做审计记录，便于排查问题、复现对话与合规留痕。

## 存储位置

- 目录：`{应用数据目录}/llm_audit/`（与 `get_app_data_dir()` 一致，和 contexts 等共用根目录）
- 文件：按 UTC 日期分文件，`llm_audit_YYYY-MM-DD.jsonl`
- 格式：每行一条 JSON，UTF-8 编码

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
  - `append_audit(direction, model, payload, meta=None)`
- 调用点：`backend/services/llm/llm_service.py`  
  - `LLMService.chat()`：请求前写 request，成功写 response，异常写 response_error，均带 `audit_id`  
  - `LLMService.stream_chat()`：同上，并处理流式中断/异常时的局部响应与 `stream_interrupted`
- 会话上下文：Orchestrator 调用 `chat` / `stream_chat` 时传入 `audit_meta={"session_id": session_id}`，故审计记录中可带 `session_id` 便于按会话检索。

## 使用方式

- 审计写入失败仅打日志，不抛异常，不影响主流程。
- 应用数据目录不可用时（如 `get_app_data_dir()` 失败），不写文件，仅 warning 日志。
- **关闭审计**：设置环境变量 `LLM_AUDIT_DISABLED=1`（或 `true`/`yes`），则不再写入任何审计记录，适用于生产环境或磁盘敏感场景。

查询示例（按 audit_id 配对一次调用）：

```bash
# 某日日志中查找同一 audit_id 的 request 与 response
grep '"audit_id":"<id>"' llm_audit_2025-02-27.jsonl
```

按会话查询：

```bash
grep '"session_id":"<session_id>"' llm_audit_2025-02-27.jsonl
```
