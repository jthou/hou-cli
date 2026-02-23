# 任务管理与展示机制设计

## 1. 目标与原则

- **单一数据源**：任务状态与结果存库，Web 仅通过 API 读写，不维护业务状态。
- **列表轻量、详情按需**：列表接口只返回列表展示所需字段（含一句结果摘要）；完整结果在「详情」按需拉取。
- **结果可展示**：执行结果有统一结构，前端能按任务类型渲染；新增任务类型时需约定 result 形状并在前端扩展展示逻辑。
- **非必要不添加**：不引入多余状态、接口或组件。

---

## 2. 任务管理验证规范（创建时）

任务创建（POST `/api/task-queue/tasks`）与 Handler 执行均遵循同一套校验约定，保证非法任务在创建阶段即被拒绝，执行阶段再次校验便于 Worker 标记失败原因。

### 2.1 校验时机

- **创建时（API）**：在写入库之前调用 `validate_task_creation(task_type, metadata)`；不通过则返回 HTTP 400，`detail` 为错误描述，不创建任务。
- **执行时（Handler）**：各 handler 可对必填参数再次校验（如缺 `location`、`url`），不通过则抛出 `ValueError`，由 Worker 写入 `tasks.error` 并标记失败。

### 2.2 校验规则

1. **task_type 白名单**  
   `task_type` 必须为 `TASK_TYPES` 中已定义的类型（如 `weather_query`、`video_download`）。否则：`无效的任务类型: {task_type}，可选: ...`。

2. **metadata 必填**  
   对 `TASK_TYPES[task_type].metadata_schema` 中 `required: true` 的字段：
   - 若缺失或为 `null`：`缺少必填参数: {field_name}`。
   - 若为字符串且经 `strip()` 后为空：`必填参数不能为空: {field_name}`。

3. **metadata 枚举**  
   若字段在 schema 中定义了 `enum`（`[{ "value": "x", "label": "..." }]`），则传入值必须属于 `value` 列表，否则：`参数 {field_name} 取值无效，可选: [...]`。

4. **其他**  
   `metadata` 非 dict 时按空对象 `{}` 处理，仍按必填与枚举规则校验。

### 2.3 实现与测试对应

| 规范项 | 实现位置 | 测试位置 |
|--------|----------|----------|
| 创建时 task_type 白名单 | `task_queue_routes.create_task` → `validate_task_creation` | `test_task_queue_routes.py`：`test_create_task_invalid_task_type` |
| 创建时必填/空串/枚举 | `task_handlers.validate_task_creation` | `test_task_handlers.py`：`TestValidateTaskCreation`；`test_task_queue_routes.py`：`test_create_task_*_missing_*`、`*_empty_*`、`*_valid_metadata_passes` |
| 执行时必填校验 | 各 `process_*_task` 内对 `location`/`url` 等校验 | `test_task_handlers.py`：`TestTaskHandlerValidation` |

新增任务类型时：在 `TASK_TYPES` 中补充 `metadata_schema`（含 `required`、`enum`），即可自动纳入上述校验与测试约定。

---

## 3. 任务状态与生命周期

### 3.1 状态枚举（仅五种）

| 状态 | 含义 |
|------|------|
| `queued` | 待执行（创建即入队，等待 Worker 拉取） |
| `running` | 执行中 |
| `completed` | 成功完成 |
| `failed` | 失败（含重试用尽） |
| `cancelled` | 已取消 |

无 `pending`、`retrying`；创建任务时直接写入 `status=queued`。

### 3.2 生命周期

- 创建：`create_task(...)` → 插入一行，`status=queued`，`queued_at=now`。
- 拉取：Worker 轮询 `status=queued`，`acquire_task` 将该行更新为 `running` 并绑定 `worker_id`。
- 完成：`complete_task(task_id, result=...)` 或 `complete_task(task_id, error=...)`；成功写 `result`（JSON），失败写 `error`；若未超重试则直接再次置为 `queued`。
- 取消：仅允许取消 `queued` 或 `running`，置为 `cancelled`。

---

## 4. 任务结果结构（存库与 API）

### 4.1 写入 result 的约定（Handler 返回值）

所有任务类型的 handler 成功时返回的 dict 会经 `complete_task(result=...)` 序列化写入 `tasks.result`。**约定**：

- 必须包含：`"status": "success"`。
- 必须包含一句摘要，供列表展示：`"summary": "人类可读一句话"`。
- 类型相关数据放在 `"data"` 或 `"result"` 中，供详情页按类型渲染。

示例：

```json
{
  "status": "success",
  "summary": "已保存至 /path/to/dir",
  "data": { "output_dir": "/path/to/dir", "title": "视频标题" }
}
```

或（天气）：

```json
{
  "status": "success",
  "summary": "北京 晴 25°C",
  "location": "北京",
  "query_type": "current",
  "result": { "current_weather": { ... } }
}
```

失败不写 `result`，只写 `tasks.error`（字符串）。

### 4.2 列表接口：GET /api/task-queue/tasks

- **用途**：列表页展示、筛选、分页。
- **返回**：每个任务为对象，**不包含完整 `result`**，但**包含**：
  - 基础字段：`task_id`, `task_type`, `task_name`, `status`, `priority`, `worker_id`, `created_at`, `started_at`, `completed_at`, `duration`, `progress`, `message`, `error`, `retry_count`。
  - **result_summary**：仅当 `status === "completed"` 且库中存在 `result` 时，从 `result` JSON 中解析出的 `summary` 字段；否则为 `null`。用于列表行内展示一句结果摘要。
- **查询参数**：`status`（可选）、`limit`、`offset`。

### 4.3 详情接口：GET /api/task-queue/tasks/:id

- **用途**：详情弹层/页按需拉取，展示完整结果。
- **返回**：单任务完整行，包含 `result`（JSON 对象）、`metadata` 等全部字段；`result` 即 4.1 约定的结构，前端按 `task_type` 渲染。

---

## 5. 前端展示机制

### 5.1 数据流

- **任务类型**：创建弹层打开时请求 `GET /api/task-queue/task-types`，按返回的 `metadata_schema` 动态渲染表单项（如天气查询的「城市名称」「查询类型」）。
- **创建任务**：提交时 `POST /api/task-queue/tasks`，body 含 `task_type`、`task_name`（可选）、`priority`、`metadata`（由 schema 必填/枚举校验后提交）。
- **列表**：进入任务管理页或刷新时请求 `GET /api/task-queue/tasks`；仅使用返回的列表项（含 `result_summary`），不在此请求中拿完整 `result`。
- **详情**：用户点击「查看详情」时，请求 `GET /api/task-queue/tasks/:id`，用返回的 `task.result` 在详情弹层中按类型展示。

### 5.2 列表行展示

- 必显：任务名、类型、状态、创建/开始/完成时间、进度（running 时）、错误信息（`error`）。
- 若 `status === "completed"` 且存在 `result_summary`：在行内展示该摘要（一句）。
- 操作：取消（queued/running）、「查看详情」（打开详情弹层并拉取该任务详情）。

### 5.3 详情弹层展示

- 基础信息：任务名、类型、状态、创建/开始/完成时间、耗时、错误（若有）。
- **执行结果**：仅当 `status === "completed"` 且存在 `task.result` 时展示；按 `task_type` 分支：
  - `video_download`：展示 `result.summary`、`result.data.title`、`result.data.output_dir`。
  - `weather_query`：展示 `result.summary`、`result.result.current_weather` 或 `result.result.forecast`。
  - 其他类型：降级为 JSON 展示。
- 失败任务只展示 `task.error`，不要求有 `result`。

### 5.4 错误字段

- API 与 DB 统一使用字段名 **error**（非 `error_message`）。前端展示时以 `task.error` 为准，可兼容历史 `error_message`。

---

## 6. 与现有组件的对应关系

| 设计项 | 实现位置 |
|--------|----------|
| 任务创建验证规范 | `task_handlers.validate_task_creation`；`task_queue_routes.create_task` 调用之 |
| 状态枚举与生命周期 | `backend/infrastructure/storage/task_queue_db.py`（TaskStatus、create_task、acquire_task、complete_task、cancel_task） |
| Handler 返回 result 形状 | `backend/infrastructure/execution/task_handlers.py`（各 process_*_task） |
| list_tasks 含 result_summary | `task_queue_db.list_tasks()` 查询 result 列并解析出 summary |
| GET list / GET detail | `backend/api/task_queue_routes.py` |
| 列表/详情展示与按类型渲染 | `frontend/react-app/src/pages/TaskManagement.jsx`（TaskCard、TaskDetailModal、TaskResultDisplay） |

---

## 7. 测试约定（TDD）

实现与重构以本文档为准；**先写文档与测试，再改实现**。

### 7.1 测试与文档对应

| 约定 | 测试位置 |
|------|----------|
| 任务创建：task_type 白名单、metadata 必填/空串/枚举（§2） | `test_task_queue_routes.py`：`test_create_task_invalid_task_type`、`test_create_task_*_missing_*`、`*_empty_*`、`*_valid_metadata_passes`；`test_task_handlers.py`：`TestValidateTaskCreation`、`TestTaskHandlerValidation` |
| list_tasks 在 completed 且 result 含 summary 时返回 result_summary | `backend/infrastructure/storage/tests/test_task_queue_db.py`：`test_list_tasks_includes_result_summary_for_completed`、`test_list_tasks_result_summary_null_*` |
| get_task 返回的 task 含完整 result 对象 | `test_task_queue_db.py`：`test_get_task_returns_full_result` |
| 列表 API 返回项含 result_summary；详情 API 返回 task.result | `backend/api/tests/test_task_queue_routes.py`：`test_list_tasks_response_includes_result_summary`、`test_get_task_response_includes_result` |
| Handler 成功返回含 status、summary、data/result | `backend/infrastructure/execution/tests/test_task_handlers.py`：`TestTaskHandlerResultShape` |

### 7.2 运行相关测试

```bash
pytest backend/infrastructure/storage/tests/test_task_queue_db.py \
       backend/api/tests/test_task_queue_routes.py \
       backend/infrastructure/execution/tests/test_task_handlers.py -v
```

### 7.3 前端

可选：E2E 或集成测试断言列表展示 result_summary、详情按类型展示 result；或单元测试 mock API 响应。当前以人工验证为主。
