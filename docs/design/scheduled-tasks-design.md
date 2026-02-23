# 定时任务设计文档

## 方案对比

### 方案1：独立定时器（Timer-based Scheduler）
**优点：**
- 职责清晰，专门用于定时任务
- 支持复杂的 cron 表达式
- 可以精确控制执行时间

**缺点：**
- 需要额外的进程/线程
- 增加系统复杂度
- 需要单独管理生命周期

### 方案2：利用现有心跳机制（推荐）
**优点：**
- 复用现有基础设施，减少资源消耗
- 统一管理，代码集中
- 实现简单，维护成本低
- 心跳机制已经稳定运行

**缺点：**
- 执行时间精度受心跳间隔影响（30秒）
- 对于需要精确到秒的任务不够精确

## 推荐方案：扩展心跳机制

### 设计思路

1. **在心跳循环中检查定时任务**
   - 心跳每30秒执行一次
   - 每次心跳检查是否有定时任务需要执行
   - 通过计算时间差判断是否到达执行时间

2. **定时任务存储**
   - 在任务队列数据库中新增 `scheduled_tasks` 表
   - 存储定时任务的配置和执行历史

3. **任务执行流程**
   ```
   心跳循环 → 检查定时任务 → 创建任务到队列 → Worker 执行
   ```

### 实现细节

#### 1. 定时任务表结构
```sql
CREATE TABLE scheduled_tasks (
    schedule_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    task_name TEXT NOT NULL,
    schedule_type TEXT NOT NULL,  -- 'interval' 或 'cron'
    schedule_config TEXT NOT NULL,  -- JSON: {"interval_seconds": 3600} 或 cron 表达式
    next_run_time TEXT NOT NULL,
    last_run_time TEXT,
    is_active INTEGER DEFAULT 1,
    metadata TEXT,  -- JSON: 任务元数据
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### 2. 心跳扩展
在 `HeartbeatMonitor._heartbeat_loop()` 中添加：
```python
# 每 10 次心跳检查一次定时任务（约5分钟）
if self.heartbeat_count % 10 == 0:
    await self.check_scheduled_tasks()
```

#### 3. 定时任务检查逻辑
```python
async def check_scheduled_tasks(self):
    """检查并执行到期的定时任务"""
    scheduled_tasks = task_queue_db.get_due_scheduled_tasks()
    for task in scheduled_tasks:
        # 创建任务到队列
        task_id = task_queue_db.create_task(...)
        # 更新下次执行时间
        task_queue_db.update_scheduled_task_next_run(...)
```

## 使用场景

### 每小时查询天气预报
```python
{
    "schedule_type": "interval",
    "schedule_config": {"interval_seconds": 3600},  # 1小时
    "task_type": "weather_query",
    "metadata": {
        "location": "北京",
        "query_type": "current"  # 或 "forecast"
    }
}
```

### 每天定时备份
```python
{
    "schedule_type": "cron",
    "schedule_config": {"cron": "0 2 * * *"},  # 每天凌晨2点
    "task_type": "backup",
    "metadata": {...}
}
```

## API 设计

### 创建定时任务
```
POST /api/task-queue/scheduled-tasks
{
    "task_type": "weather_query",
    "task_name": "每小时查询北京天气",
    "schedule_type": "interval",
    "schedule_config": {"interval_seconds": 3600},
    "metadata": {"location": "北京"}
}
```

### 列出定时任务
```
GET /api/task-queue/scheduled-tasks
```

### 启用/禁用定时任务
```
PUT /api/task-queue/scheduled-tasks/{schedule_id}/toggle
```

### 删除定时任务
```
DELETE /api/task-queue/scheduled-tasks/{schedule_id}
```

## 优势

1. **资源效率**：复用心跳机制，无需额外进程
2. **统一管理**：所有定时任务和普通任务在同一系统中
3. **可靠性**：利用现有的 Worker 和重试机制
4. **可扩展**：未来可以支持更复杂的调度需求
