# 任务管道设计：上游输出作为下游输入

本文档描述如何在不破坏现有单任务能力的前提下，支持「任务管道」：下游任务的输入来自上游任务的输出（如：视频提音频 → 语音转文字）。

---

## 适用场景说明（单用户本机）

本设计**针对单用户、本机运行**场景做了简化，可直接按此实施：

- **无需**多用户权限校验与访问控制
- **保留**基本的路径与依赖安全（如循环依赖检测、路径在主目录下）
- **不要求**复杂缓存、高并发或深度依赖链优化
- **监控**以基础日志与简单执行状态展示为主，无需复杂链路追踪

若后续扩展为多用户或分布式，可在本方案基础上增加权限、审计与性能优化。

---

## 1. 目标与范围

- **目标**：支持「上游任务输出 = 下游任务输入」的链式执行，无需用户手动复制路径或分两次创建。
- **典型场景**：
  - 视频提取音频 → 语音转文字（`video_extract_audio` 的 `output_file` → `speech_to_text` 的 `input_file`）
  - 视频下载（仅音频）→ 语音转文字
  - 任意「产出文件路径」的任务 → 消费「输入文件路径」的任务
- **非目标（一期）**：通用 DAG 工作流、多分支、条件分支、循环；可留作后续扩展。

---

## 2. 方案选型

### 2.1 方案 A：任务级依赖（推荐一期）

- **思路**：在现有「任务」上增加**依赖**与**输入解析**，不引入新实体。
- **数据**：每个任务可选「依赖一个上游任务」+「本任务哪些字段从上游 result 里取」。
- **执行**：下游任务创建时入队但 **acquire 时仅当其依赖任务已完成才可被拉取**；被拉取时用上游 result 解析并填充 metadata，再执行。
- **优点**：实现小、与现有 API/DB 兼容好，前端可先支持「创建任务时选择：输入来自某任务」。
- **缺点**：一条链需要用户依次创建多个任务（或前端提供「管道模板」一次创建多个带依赖的任务）。

### 2.2 方案 B：管道实体（Pipeline）

- **思路**：新增「管道」实体，包含多个步骤及步骤间输入输出映射；执行时按序实例化为任务并注入上一步输出。
- **优点**：一次创建整条管道、可展示管道级状态。
- **缺点**：需要新表、新 API、前端管道编排 UI，工作量较大。

**建议**：一期采用 **方案 A（任务级依赖）**，为后续方案 B 预留扩展（例如：管道 = 多个带依赖关系的任务 + 一个 pipeline_id 分组）。

---

## 3. 方案 A 详细设计（任务级依赖）

### 3.1 数据模型（单用户简化版）

在 **tasks** 表增加字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `depends_on_task_id` | TEXT NULL | 依赖的上游任务 ID；NULL 表示无依赖 |
| `input_bindings` | TEXT NULL (JSON) | 从上游 result 解析到本任务 metadata 的映射 |

*单用户本机场景下无需权限相关字段，仅上述两字段即可。*

**input_bindings** 格式示例（键为本任务 metadata 字段名，值为上游 result 的 JSON 路径）：

```json
{
  "input_file": "result.data.output_file"
}
```

或支持多级路径（可用 JSONPath 或 JMESPath 或简单点号路径）：

- `result.data.output_file` → 上游任务 `result["data"]["output_file"]`
- `result.summary` → 上游任务 `result["summary"]`

约定：仅当 `depends_on_task_id` 非空时解析 `input_bindings`；解析结果**合并**进当前任务的 `metadata`（不覆盖未在 bindings 中列出的字段）。

### 3.1.1 任务类型的输入/输出描述（管道可链接性）

为支持管道编排时**判断上下游是否可链接**，建议在任务类型定义中增加与输入/输出相关的 metadata，供前端或 API 筛选「可接在本任务前面的上游」、推荐绑定关系。

- **输出描述（pipeline_outputs）**  
  描述该任务类型**完成后**在 `result` 中产出的、可供下游消费的「端口」：
  - 每项：`path`（如 `result.data.output_file`）、`type`（如 `file`）、`format`（如 `audio` / `video` / `text`）、可选 `description`。
  - 示例：`video_extract_audio` 产出 `result.data.output_file`，type=file，format=audio；`speech_to_text` 产出 `result.data.output_file`（字幕/文本路径），type=file，format=text。

- **输入描述（在 metadata_schema 中扩展）**  
  对可由上游结果填充的字段，在 schema 中增加 **pipeline_accept**（可选）：
  - `type`：接受类型，如 `file`。
  - `formats`：接受格式列表，如 `["audio", "video"]`，表示该输入可接受音频或视频文件路径。
  - 编排时：上游某 `pipeline_outputs[].format` 落在下游某字段的 `pipeline_accept.formats` 内，且 type 一致，则可推荐绑定该 path → 该字段。

- **可链接判断**  
  - 上游任务类型 A 的 `pipeline_outputs` 中至少有一项 `(type, format)`；  
  - 下游任务类型 B 的 `metadata_schema` 中某字段的 `pipeline_accept` 与该 `(type, format)` 兼容；  
  - 则 A 与 B 可链接，可推荐绑定：A 的该项 `path` → B 的该字段名。  
  - API 可提供「可链接的上游任务类型」或「推荐绑定」列表；前端创建下游时仅展示已完成且任务类型可链接的上游任务，并预填或校验绑定。

### 3.2 任务创建（单用户简化版）

- **API**：`POST /api/task-queue/tasks` 请求体在现有基础上增加可选字段：
  - `depends_on_task_id`：上游任务 ID
  - `input_bindings`：同上
- **校验**（简化，无多用户权限校验）：
  - `depends_on_task_id` 对应的任务必须存在且未取消；
  - 禁止循环依赖（A 依赖 B，B 依赖 A）：校验「上游任务不能依赖当前任务」即可；
  - `input_bindings` 的 key 必须是当前 `task_type` 的 metadata_schema 中存在的字段。
- **创建时**：任务仍以 `status=queued` 写入；不在此刻解析 bindings（上游可能尚未完成）。

### 3.3 获取任务（acquire_task）逻辑变更

当前逻辑：`SELECT ... WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1`。

**变更**：

- 仅当任务**可执行**时才可被 acquire：
  - 若 `depends_on_task_id` 为 NULL → 与现有一致，可直接 acquire；
  - 若 `depends_on_task_id` 非 NULL → 仅当该上游任务 `status = 'completed'` 且 `result` 非空时才可被 acquire。
- SQL 示例（思路）：  
  `LEFT JOIN tasks dep ON dep.task_id = t.depends_on_task_id`  
 条件中增加：`(t.depends_on_task_id IS NULL OR (dep.status = 'completed' AND dep.result IS NOT NULL))`。

这样下游任务会一直留在队列中直到上游完成，且不会被「提前」执行。

### 3.4 执行前解析：用上游 result 填充 metadata

在 **Worker 真正执行 handler 之前**（例如在 `_execute_task` 内，调用 `handler(task_info)` 之前）：

1. 若 `task_info["depends_on_task_id"]` 存在，则从 DB 读取该任务的 `result`（JSON）。
2. 根据 `task_info["input_bindings"]`，对每个 `(metadata_key, path)`：
   - 从上游 `result` 中用 path 取出值（如 `result.data.output_file`）；
   - 将得到的值写入 `task_info["metadata"][metadata_key]`（若 path 取不到值可报错或跳过，由实现决定）。
3. 将**解析后的** `task_info` 传给 handler，handler 无需感知依赖，只看到「已经填好的 metadata」。

这样现有 handler 逻辑完全不用改，只需在 Worker 层增加「解析依赖并合并 metadata」的一步。

### 3.4.1 上下游输入是否匹配（判断逻辑）

- **创建时**  
  - 只做**静态校验**：`input_bindings` 的 **key** 必须在下游任务类型的 `metadata_schema` 中存在（即下游是否有该字段）。  
  - **不校验**上游 result 是否包含这些 path（上游可能尚未完成），也不校验 path 对应的值类型或格式。

- **执行时（Worker 解析后）**  
  - 按 path 从上游 result 取值；若某 path 不存在或为 null，该 key **不会**写入 metadata（当前实现为跳过）。  
  - **匹配检查（建议）**：若本任务有 `input_bindings`，解析后检查其中在 `metadata_schema` 里为 **required** 的字段是否都拿到了非空值；若有缺失，则**不调用 handler**，直接将该任务标记为失败，error 写明「管道输入不匹配：上游 result 未解析到 xxx（path: …）」，便于排查。

- **可选增强**  
  - 创建时若上游**已完成**：可校验上游 result 是否包含 bindings 中的 path，不包含则拒绝创建或给出警告。  
  - 值层面：如 `input_file` 解析出路径后，可选校验文件是否存在（可由 handler 或 Worker 层统一做）。

### 3.5 上游失败 / 取消时的下游行为

- **上游失败（failed）或取消（cancelled）**：依赖它的下游任务不应再执行。
  - 做法一：在 **complete_task（上游标记为 failed/cancelled）** 时，将所有 `depends_on_task_id = 该任务` 的下游任务标记为 `cancelled` 或 `failed`，并写入 error 如「上游任务失败，管道终止」。
  - 做法二：acquire 时若发现上游为 failed/cancelled，则永远不选中该下游；但下游会一直占着「待执行」状态，需定期清理或单独状态。  
  **推荐做法一**：上游失败/取消时，将依赖其的下游任务一并标记为失败/取消，并可选地递归处理「依赖这些下游」的再下游，避免僵尸任务。

### 3.6 超时与重试

- 下游任务超时：与现有一致，按该任务的 `task_type` 配置超时。
- 下游任务重试：与现有一致；重试时再次用**当前**上游 result 解析 metadata（上游 result 已固定，不会变）。
- 上游重试后成功：若下游尚未被 acquire，则上游完成后下游变为可执行；若下游已被标记为「因上游失败而取消」，则需考虑是否允许「上游重试成功后重新激活下游」（一期可不做，保持简单：上游失败即下游取消）。

---

## 4. 方案 B 预留（管道实体）要点

若后续做「管道」实体，建议：

- **pipeline** 表：pipeline_id, name, definition (JSON), status, created_at 等。
- **definition** 示例：`{ "steps": [ { "task_type": "video_extract_audio", "metadata": { "input_file": "用户填" } }, { "task_type": "speech_to_text", "metadata": {}, "input_bindings": { "input_file": "steps[0].result.data.output_file" } } ] }`。
- 执行：创建 pipeline 时顺次创建 step 对应的 task，从第二步起 `depends_on_task_id` = 上一步的 task_id，`input_bindings` 从 definition 来；或先只创建第一步任务，在上一步完成时再创建并入队下一步（与方案 A 的「下游入队」一致，只是创建时机由管道引擎触发）。

方案 A 的 `depends_on_task_id` + `input_bindings` 可直接复用于方案 B 中「每个 step 对应任务」的依赖与解析。

---

## 5. API 设计（方案 A）

### 5.1 创建任务（扩展）

- **POST** `/api/task-queue/tasks`
- 请求体在现有基础上增加（均可选）：
  - `depends_on_task_id`: string | null
  - `input_bindings`: { "metadata_key": "result.path.to.value" } | null
- 校验：见 3.2。

### 5.2 列表 / 详情

- 列表与详情响应中增加 `depends_on_task_id`、`input_bindings` 字段，便于前端展示「依赖谁」「输入从哪来」。
- 可选：在任务详情中返回 `resolved_metadata`（执行前解析后的 metadata），仅当任务已在执行或已完成时存在，便于排查。

### 5.3 取消行为

- 取消某任务时，可选：是否级联取消「依赖该任务的所有下游任务」（建议默认 true）。

---

## 6. 前端与产品行为（建议）

- **创建任务**：在表单中增加「输入来源」：
  - 选项一：「手动填写」→ 与现在一致；
  - 选项二：「来自已有任务」→ 选择任务（仅列出已完成且 result 含所需路径的任务），再选择「用该任务的哪个输出填到本任务的哪个字段」（可由常见管道预设：如「上一任务的 output_file → 本任务 input_file」）。
- **任务列表/详情**：展示「依赖：任务 A」「输入绑定：input_file ← A.result.data.output_file」等，便于理解管道关系。
- **管道模板（可选）**：提供「视频提音频 → 语音转文字」等一键创建两个任务（第二个自动带 `depends_on_task_id` 和 `input_bindings`），减少重复操作。

---

## 7. 实施清单（方案 A · 单用户简化版）

| 步骤 | 项 | 说明 |
|------|----|------|
| 1 | DB 迁移 | tasks 表增加 depends_on_task_id、input_bindings 字段 |
| 2 | create_task | 支持写入依赖与输入绑定；校验上游存在、禁止循环依赖 |
| 3 | acquire_task | 仅返回「无依赖或依赖已完成且 result 非空」的 queued 任务 |
| 4 | Worker 执行前 | 从上游 result 按 input_bindings 解析并合并到 task_info.metadata，再调用 handler |
| 5 | complete_task | 上游失败/取消时，将依赖其的下游任务标记为失败或取消 |
| 6 | API | POST tasks 接受 depends_on_task_id、input_bindings；GET 返回该两字段 |
| 7 | 前端 | 简单的「输入来自某任务」选择与字段映射；列表/详情展示依赖与绑定 |
| 8 | 测试 | 重点测试核心链路（创建 A → 创建依赖 A 的 B → A 完成后 B 正确执行），边界场景可适度简化 |

*单用户本机下无需复杂缓存、依赖链深度限制或批量处理优化，按上述步骤即可。*

---

## 7.1 实施与设计一致性验证

实施完成后，可通过以下方式确认实现与本文档设计一致。

### 方式一：设计→实现追溯表

每完成一项实施清单，在下面表格中填写对应代码位置或测试用例，便于复查与回归。

| 设计要点（见上文章节） | 实现位置（文件: 函数/类或表） | 验证方式（测试名或手动步骤） |
|------------------------|-------------------------------|------------------------------|
| 3.1 表增加 depends_on_task_id、input_bindings | task_queue_db.py: _init_db 迁移 + list_tasks/get_task/acquire_task SELECT | test_create_task_with_dependency_and_bindings（list/get 含两字段） |
| 3.2 创建时写入并校验：上游存在、禁止循环、bindings 的 key 在 schema 中 | task_queue_db.create_task + check_dependency_cycle；task_queue_routes 创建前校验 | test_create_task_depends_on_nonexistent_upstream_returns_400；test_create_task_depends_on_cancelled_upstream_returns_400；test_create_task_cycle_dependency_returns_400 |
| 3.3 acquire 仅返回「无依赖或依赖已完成」的 queued | task_queue_db.acquire_task（LEFT JOIN dep，条件 dep.status=completed AND dep.result IS NOT NULL） | test_acquire_task_skips_dependent_until_upstream_completes |
| 3.4 执行前用上游 result 解析并合并 metadata | task_worker._resolve_input_bindings；pipeline_resolve.resolve_input_bindings_from_result | test_pipeline_resolve.py（解析逻辑单元测）；GET 详情返回 resolved_metadata |
| 3.5 上游失败/取消时下游标记失败或取消 | task_queue_db.complete_task（最终失败时 UPDATE 下游 failed）；cancel_task（级联 UPDATE 下游 cancelled） | test_cascade_fail_when_upstream_fails；test_cancel_task |
| 5.1 POST 接受 depends_on_task_id、input_bindings | task_queue_routes.create_task 请求体 + 校验后传 create_task(..., depends_on_task_id=, input_bindings=) | 带两字段创建 200，GET 详情含两字段；test_create_task_with_dependency_and_bindings |
| 5.2 GET 列表/详情返回两字段 | task_queue_db.list_tasks/get_task 返回；task_queue_routes 透传；可选 resolved_metadata | 列表/详情响应含 depends_on_task_id、input_bindings |
| 6 前端：输入来源可选「来自某任务」、列表/详情展示依赖与绑定 | TaskManagement.jsx CreateTaskModal（输入来源 + 字段映射）、TaskCard/ TaskDetailModal 展示 | 手动：创建下游选上游与绑定；列表/详情见「依赖」「绑定」「解析后 metadata」；管道模板一键创建 |

### 方式二：验收测试用例（可自动化）

以下用例通过即认为与设计一致；建议写成 pytest（或等价）便于持续回归。

1. **无依赖任务行为不变**  
   - 创建任务不传 `depends_on_task_id` / `input_bindings`，任务可被 acquire 并正常执行，结果与现有单任务一致。

2. **有依赖：上游未完成时下游不可被拉取**  
   - 创建任务 A（无依赖）；创建任务 B，`depends_on_task_id=A`，`input_bindings={"input_file":"result.data.output_file"}`。  
   - 在 A 未完成前，acquire 不应返回 B；仅当 A 已完成且 result 非空时，acquire 可返回 B。

3. **有依赖：下游执行时 metadata 已解析**  
   - 同上，A 完成后 result 含 `data.output_file="/path/to/out.mp3"`。  
   - B 被拉取并执行时，传入 handler 的 `task_info["metadata"]["input_file"]` 应为 `"/path/to/out.mp3"`（或等价路径），且 B 的 handler 无需改即可消费该路径。

4. **创建校验：上游不存在或已取消**  
   - `depends_on_task_id` 为不存在的 task_id → 400 或明确错误。  
   - `depends_on_task_id` 为已取消任务 → 400 或明确错误（若设计允许依赖已取消任务则可放宽）。

5. **创建校验：循环依赖**  
   - 存在任务 A；创建 B 依赖 A；再创建 C 依赖 B；尝试创建 A 依赖 C（或直接 A 依赖 B、B 依赖 A）→ 应拒绝并返回 400 或明确错误。

6. **上游失败后下游状态**  
   - 创建 A、B（B 依赖 A）。将 A 标记为 failed（或取消）。  
   - B 应变为 failed 或 cancelled，且 error/result 中含「上游失败」或「管道终止」类说明。

7. **API 与存储**  
   - POST 创建时传 `depends_on_task_id`、`input_bindings`，响应或 GET 详情中能读到相同值；列表接口返回的该任务也含这两字段。

**对应 pytest 用例（backend）**  
- 用例 1：由既有单任务创建/acquire 测试覆盖，不传依赖即可。  
- 用例 2：`test_task_queue_db.py::TestTaskQueueDB::test_acquire_task_skips_dependent_until_upstream_completes`  
- 用例 3：执行时 metadata 解析由 `pipeline_resolve.resolve_input_bindings_from_result` + Worker 保证；GET 详情 `resolved_metadata` 可人工/集成验证。  
- 用例 4：`test_create_task_depends_on_nonexistent_upstream_returns_400`、`test_create_task_depends_on_cancelled_upstream_returns_400`  
- 用例 5：`test_create_task_cycle_dependency_returns_400`  
- 用例 6：`test_task_queue_db.py::TestTaskQueueDB::test_cascade_fail_when_upstream_fails`；取消级联由 `cancel_task` 实现 + `test_cancel_task` 覆盖。  
- 用例 7：`test_create_task_with_dependency_and_bindings`（list/get 含两字段）

### 方式三：实现后检查清单

实现完成后逐项勾选，确保无遗漏。

- [x] tasks 表存在 `depends_on_task_id`、`input_bindings` 且类型/含义与 3.1 一致。
- [x] create_task 支持写入两字段，且校验：上游存在、未取消、无循环、bindings 的 key 在 schema 中（与 3.2 一致）。
- [x] acquire_task 的 SQL/逻辑满足 3.3（仅返回可执行任务）。
- [x] Worker 在执行 handler 前完成 3.4 的解析与合并，且 handler 不改动即可用。
- [x] 上游失败/取消时，依赖其的下游按 3.5 被标记为失败或取消。
- [x] POST/GET 行为符合 5.1、5.2；取消行为符合 5.3（级联取消已实现）。
- [x] 前端行为与第 6 节建议一致（可选「来自某任务」、列表/详情展示依赖与绑定、管道模板「视频提音频→语音转文字」）。
- [x] 方式二中的验收用例全部通过（自动化：test_task_queue_db + test_task_queue_routes 中管道相关用例；无依赖行为由既有单任务用例覆盖）。

若上述三项（追溯表、验收用例、检查清单）均满足，可认为实施与设计一致；后续改动时用同一套用例做回归。

---

## 8. 小结

- **最小改动支持管道**：任务级依赖（depends_on_task_id）+ 输入绑定（input_bindings）+ acquire 时过滤 + 执行前解析 metadata。
- **现有 handler 无需改**：解析在 Worker 层完成，handler 只看到「已填好的 metadata」。
- **单用户本机**：不引入权限与多租户逻辑，校验与实施清单已按该场景简化，可直接落地。
- **扩展**：后续可在此基础上增加「管道」实体、多用户或分布式时，再补充权限、审计与性能优化。

本文档为任务管道的设计说明，实现时以方案 A 为准，并与现有单任务行为保持兼容。
