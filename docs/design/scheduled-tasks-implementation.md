# 定时任务实现设计

本文档基于前期讨论，描述定时任务的完整实现方案。

**实施状态**：✅ 已完成（2025-02-27）

---

## 1. 设计约束（来自前期讨论）

- **不增加 `at` 类型**：一次性任务不纳入定时任务，仅支持 `interval` 和 `cron`
- **错误指数退避**：失败后延迟重试，避免重试风暴
- **调度精度**：视需求决定是否引入专用定时器；若引入，定时器总数需有限制
- **心跳检查**：心跳程序负责检查定时任务状态，是定时任务检查的主入口

---

## 2. 数据库设计

### 2.1 scheduled_tasks 表

```sql
CREATE TABLE scheduled_tasks (
    schedule_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    task_name TEXT NOT NULL,
    schedule_type TEXT NOT NULL,       -- 'interval' | 'cron'
    schedule_config TEXT NOT NULL,     -- JSON
    next_run_time TEXT NOT NULL,       -- ISO 8601
    last_run_time TEXT,                -- ISO 8601，上次成功创建任务的时间
    is_active INTEGER DEFAULT 1,
    consecutive_errors INTEGER DEFAULT 0,  -- 连续失败次数，用于错误退避
    last_error TEXT,                   -- 最近一次失败原因（可选，便于排查）
    metadata TEXT,                     -- JSON，传给 create_task 的 metadata
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 2.2 新增列（兼容已有库）

对已有 `scheduled_tasks` 表，启动时补列：

- `consecutive_errors` INTEGER DEFAULT 0
- `last_error` TEXT

### 2.3 tasks 表可选溯源字段

在 `tasks` 表增加 `created_by_schedule_id`（可选）：

- 用于追溯任务由哪个定时任务创建
- 创建时由 `create_task(..., created_by_schedule_id=schedule_id)` 传入

---

## 3. schedule_config 格式

### 3.1 interval

```json
{
  "interval_seconds": 3600
}
```

- `interval_seconds`：必填，整数，≥ 60
- 下次运行 = `last_run_time + interval_seconds`（若 last_run_time 为空则用 created_at）

### 3.2 cron

```json
{
  "cron": "0 2 * * *",
  "tz": "Asia/Shanghai"
}
```

- `cron`：必填，标准 cron 表达式（分 时 日 月 周）
- `tz`：可选，时区，默认本地时区
- 使用 `croniter` 计算下次运行时间

---

## 4. 错误退避

失败时（创建任务抛异常或校验失败）不更新 `next_run_time` 为正常下次时间，而是应用退避：

| 连续失败次数 | 退避延迟 |
|-------------|----------|
| 1           | 30 秒    |
| 2           | 1 分钟   |
| 3           | 5 分钟   |
| 4           | 15 分钟  |
| 5+          | 60 分钟  |

- `next_run_time = now + 退避延迟`
- `consecutive_errors += 1`
- `last_error = 错误信息`
- 成功创建任务后：`consecutive_errors = 0`，`last_error = NULL`，`last_run_time = now`

---

## 5. 下次运行时间计算

**时间约定**：后端统一 UTC（`shared.time_utils`），前端 `toLocaleString` 自动转本地显示。

### 5.1 函数签名

```python
def compute_next_run_time(
    schedule_type: str,
    schedule_config: dict,
    last_run_time: Optional[str],
    created_at: str,
    now: Optional[datetime] = None,
) -> str:
    """返回 ISO 8601 格式的下次运行时间"""
```

### 5.2 interval 逻辑

- **首次**（`last_run_time is None`）：立即执行，`next_run_time = now`
- **之后**：`next_dt = last_run_time + interval_seconds`；若已过则按周期对齐

### 5.3 cron 逻辑

```python
# 使用 croniter
from croniter import croniter
from datetime import datetime

tz = schedule_config.get("tz")  # 或 None 用本地
cron_expr = schedule_config.get("cron", "")
iter = croniter(cron_expr, now, ret_type=datetime)
next_dt = iter.get_next()
return next_dt.isoformat()
```

---

## 6. TaskQueueDB 方法

### 6.1 create_scheduled_task

```python
def create_scheduled_task(
    self,
    task_type: str,
    task_name: str,
    schedule_type: str,
    schedule_config: dict,
    metadata: Optional[dict] = None,
) -> str:
```

- 校验 `schedule_type in ("interval", "cron")`
- 校验 `schedule_config` 格式
- 计算初始 `next_run_time`
- 插入 `scheduled_tasks`，返回 `schedule_id`

### 6.2 get_due_scheduled_tasks

```python
def get_due_scheduled_tasks(self) -> List[Dict[str, Any]]:
```

- `WHERE is_active = 1 AND datetime(next_run_time) <= datetime('now')`（兼容 ISO 格式）
- 按 `next_run_time` 升序
- 返回完整行（含 schedule_id, task_type, task_name, metadata, schedule_type, schedule_config 等）

### 6.3 update_scheduled_task_next_run（成功路径）

```python
def update_scheduled_task_after_success(
    self,
    schedule_id: str,
    schedule_type: str,
    schedule_config: dict,
    last_run_time: str,
) -> bool:
```

- 计算 `next_run_time = compute_next_run_time(...)`
- `consecutive_errors = 0`, `last_error = NULL`, `last_run_time = last_run_time`
- `updated_at = now`

### 6.4 update_scheduled_task_on_failure（失败路径）

```python
def update_scheduled_task_on_failure(
    self,
    schedule_id: str,
    error: str,
) -> bool:
```

- `consecutive_errors += 1`
- `last_error = error`
- `next_run_time = now + error_backoff(consecutive_errors)`
- `updated_at = now`

### 6.5 list_scheduled_tasks

```python
def list_scheduled_tasks(self, active_only: bool = False) -> List[Dict[str, Any]]:
```

### 6.6 toggle_scheduled_task

```python
def toggle_scheduled_task(self, schedule_id: str, is_active: bool) -> bool:
```

### 6.7 delete_scheduled_task

```python
def delete_scheduled_task(self, schedule_id: str) -> bool:
```

---

## 7. 心跳集成

### 7.1 检查频率

- 每次心跳都检查定时任务（不再每 10 次检查一次），提高响应速度
- 或保持每 10 次（约 5 分钟）以降低 DB 压力，由实现决定；**建议每次心跳检查**

### 7.2 check_scheduled_tasks 流程

```python
async def check_scheduled_tasks(self, task_queue_db):
    due_tasks = task_queue_db.get_due_scheduled_tasks()
    for scheduled_task in due_tasks:
        try:
            # 1. 校验 task_type 与 metadata（与 API 创建共用）
            ok, err = validate_task_creation(
                scheduled_task["task_type"],
                scheduled_task.get("metadata", {}),
            )
            if not ok:
                task_queue_db.update_scheduled_task_on_failure(
                    schedule_id=scheduled_task["schedule_id"],
                    error=err,
                )
                continue

            # 2. 创建任务
            task_id = task_queue_db.create_task(
                task_type=scheduled_task["task_type"],
                task_name=scheduled_task["task_name"],
                priority=TaskPriority.NORMAL,
                metadata=scheduled_task.get("metadata", {}),
                created_by_schedule_id=scheduled_task["schedule_id"],  # 可选
            )

            # 3. 更新成功状态
            now = datetime.now().isoformat()
            task_queue_db.update_scheduled_task_after_success(
                schedule_id=scheduled_task["schedule_id"],
                schedule_type=scheduled_task["schedule_type"],
                schedule_config=scheduled_task["schedule_config"],
                last_run_time=now,
            )
        except Exception as e:
            task_queue_db.update_scheduled_task_on_failure(
                schedule_id=scheduled_task["schedule_id"],
                error=str(e),
            )
```

---

## 8. 与普通任务的共通

| 项目           | 说明                                           |
|----------------|------------------------------------------------|
| task_type      | 共用，决定 handler                             |
| task_name      | 共用                                           |
| metadata       | 共用，传给 handler                             |
| validate_task_creation | 创建前校验，API 与心跳共用              |
| create_task    | 同一方法，定时任务触发时传入 created_by_schedule_id（可选） |
| task_handlers  | 完全共用，不区分来源                           |

---

## 9. 依赖

- `croniter`：解析 cron 表达式，计算下次运行时间
- 在 `requirements.txt` 增加：`croniter>=2.0.0`

---

## 10. 实施清单

| 步骤 | 项 | 说明 | 状态 |
|------|----|------|------|
| 1 | 依赖 | 添加 croniter | ✅ |
| 2 | 补列 | _init_db 中为 scheduled_tasks 补 consecutive_errors、last_error | ✅ |
| 3 | 模块 | 新建 `backend/infrastructure/schedule.py`，实现 compute_next_run_time、error_backoff_seconds | ✅ |
| 4 | task_queue_db | 实现 create_scheduled_task、get_due_scheduled_tasks、update_scheduled_task_after_success、update_scheduled_task_on_failure、list_scheduled_tasks、toggle_scheduled_task、delete_scheduled_task | ✅ |
| 5 | create_task | 增加 created_by_schedule_id 参数及 tasks 表补列 | ✅ |
| 6 | heartbeat | 更新 check_scheduled_tasks：校验、成功/失败分支、调用新方法 | ✅ |
| 7 | API | 确认 task_queue_routes 的 create 校验与 schedule_config 格式一致 | ✅ |
| 8 | 测试 | 单元测试：compute_next_run_time、get_due、成功/失败更新逻辑 | ✅ |
| 9 | 前端 | CreateScheduledTaskModal、ScheduledTaskCard（启用/禁用、删除、next_run_time、last_error） | ✅ |
| 10 | Web/static | showCreateScheduledTaskModal、submitCreateScheduledTask、toggle 修复、展示 next_run_time/last_error | ✅ |
| 11 | API 溯源 | get_task、list_tasks 返回 created_by_schedule_id | ✅ |
| 12 | Alembic 迁移 | 20250227100000 补列 created_by_schedule_id、consecutive_errors、last_error | ✅ |
| 13 | 心跳测试 | test_heartbeat_scheduled_tasks：空、成功、校验失败、create 异常 | ✅ |

---

## 11. 使用说明

### 创建定时任务
- **API**：`POST /api/task-queue/scheduled-tasks`，body 含 `task_type`、`task_name`、`schedule_type`、`schedule_config`、`metadata`
- **前端**：任务管理 → 定时任务 Tab → 点击「创建定时任务」

### 执行流程
1. 心跳每 30 秒运行一次，每次都会检查 `get_due_scheduled_tasks()`
2. 到期任务：校验 `task_type` 与 `metadata` → 调用 `create_task` 入队 → 更新 `next_run_time`
3. 失败时：`update_scheduled_task_on_failure` 应用错误退避

### 迁移
- **启动时**：`_init_db` 自动补列，无需手动操作
- **部署时**（可选）：`make migrate` 或 `cd backend && alembic upgrade head` 执行版本化迁移

---

## 12. 定时器数量限制（预留）

若后续引入专用定时器（asyncio 或 threading.Timer）：

- 配置项 `max_scheduled_tasks` 或 `max_active_timers`
- 超过限制时拒绝创建新定时任务，或仅对最早 next_run_time 的 N 个设置定时器
- 当前方案依赖心跳，无独立定时器，无需实现此限制
