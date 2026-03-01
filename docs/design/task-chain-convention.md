# 任务链约定：Handler 内创建子任务与链尾清理

本文档约定「主任务在 handler 内创建子任务」的用法及链上资源清理责任，与现有 `depends_on_task_id` / `pipeline_id` 并存，不替代依赖与管道语义。

---

## 1. 适用场景

- 主任务执行到某一步后需要**分解为多条子任务**入队，由 Worker 逐个执行（如：大 PDF 拆成多块，每块一个子任务）。
- 子任务与主任务存在**归属关系**（谁拆出来的、链上序号、谁收尾），用于 UI 分组与清理责任。

---

## 2. 数据模型（已实现）

任务表已支持以下字段（见 `task_queue_db` 迁移与 `create_task` 参数）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `parent_task_id` | TEXT NULL | 若本任务由某任务分解而来，指向该父任务；主任务为 NULL。 |
| `chain_id` | TEXT NULL | 同一条链共用同一 ID（如 UUID），便于按链查询、折叠展示。 |
| `chain_index` | INTEGER NULL | 本任务在链中的序号（0-based）。 |
| `chain_total` | INTEGER NULL | 本链子任务总数。 |
| `is_chain_tail` | INTEGER 0/1 | 是否为链尾；链尾任务负责清理链上共享资源。 |

与 `depends_on_task_id` 的关系：

- **依赖**：表示「本任务要等某任务完成且用其 result 做输入」。
- **父子/链**：表示「本任务是谁拆出来的、在链中第几个、是否收尾」。
- 子任务可以既有 `parent_task_id` 又有 `depends_on_task_id`（等父任务 result 再跑），也可以只有 `parent_task_id`（主任务创建时已把本块所需信息写入子任务 metadata，无需读父 result）。

---

## 3. Handler 内创建子任务的约定

### 3.1 允许在 handler 内调用 create_task

- 主任务 handler 执行到「分解」步骤后，**允许**调用 `get_task_queue_db().create_task(...)` 创建一条或多条子任务。
- 创建子任务时应传入：
  - `parent_task_id`：当前主任务 ID（`task_info["task_id"]`）。
  - `chain_id`：本链唯一 ID（主任务生成，如 `str(uuid.uuid4())`），所有本链子任务共用。
  - `chain_index` / `chain_total`：序号与总数。
  - `is_chain_tail`：仅链上**最后一个**子任务为 `True`。
- 子任务所需输入：通过**子任务的 metadata** 传入（如 `temp_pdf_path`、`page_from`、`page_to`、`wiki_title_base`），不依赖主任务 result 亦可；若需从主任务 result 取输入，可设 `depends_on_task_id = parent_task_id` 并用 `input_bindings`。

### 3.2 主任务完成时机

- 主任务在「创建完所有子任务并入队」后即可**立即完成**，result 中可记录 `chain_id`、子任务数量、临时资源路径（供链尾清理使用）。
- 主任务**不应**在 result 中存放过大数据（如整本 PDF 文本）；大资源应落盘，路径写入 result 或由子任务 metadata 传递。

### 3.3 幂等与重复创建

- 若主任务可能重试，创建子任务前应**幂等**：例如根据 `chain_id` 查询是否已有该链子任务，有则不再创建；或约定「主任务只创建一次子任务，重试时跳过创建」。

---

## 4. 链尾任务与资源清理

### 4.1 责任归属

- **链尾任务**（`is_chain_tail = True`）在**本任务执行结束时**负责清理本链共享资源（如主任务下载的临时 PDF 路径）。
- 链尾如何得知要删哪些资源：主任务 result 中写入共享资源路径（如 `temp_pdf_path`）；链尾任务通过 `parent_task_id` 取主任务 result，读取路径并删除；或主任务创建子任务时把 `temp_pdf_path` 写入每个子任务 metadata，链尾从自身 metadata 读取并删除。

### 4.2 主任务失败或取消

- 若主任务在**创建子任务之前**失败：无共享资源，无需清理。
- 若主任务在**创建子任务之后**失败或取消：已入队的子任务可照常执行；链尾完成时仍按约定清理。若希望「主任务取消则整链取消」，需调度层支持「按 `chain_id` 取消未执行的子任务」并在主任务取消时触发（可选，后续扩展）。

---

## 5. 前端与 API

- 列表/详情可按 `chain_id` 或 `parent_task_id` 分组，主任务下折叠展示「子任务 #1..#N」，链尾可标出「负责清理」。
- 进度可汇总为「链上已完成数 / chain_total」。
- API 创建任务时，当前**不**暴露 `parent_task_id` / `chain_id` 等链字段给前端；这些由 handler 内部在创建子任务时写入。若需「用户创建的管道」与「系统生成的链」区分，可继续用 `pipeline_id` 表示用户编排，`chain_id` 表示系统分解的链。

---

## 6. 实施状态

- **已完成**：任务表链字段、`create_task` 参数、`get_task` / `list_tasks` 返回链字段；约定文档（本文档）。
- **待后续**：具体任务类型（如 pdf_to_wiki 二期）在 handler 内创建子任务、链尾清理逻辑、前端按 chain_id 分组/折叠展示。
