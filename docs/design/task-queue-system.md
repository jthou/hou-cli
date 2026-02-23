# 任务队列系统设计文档

## 概述

任务队列系统是一个基于数据库的分布式任务处理系统，支持任务创建、排队、执行、监控和重试。Worker 进程与心跳进程协作，确保任务的可靠执行。

## 架构设计

### 核心组件

1. **任务队列数据库 (TaskQueueDB)**
   - 存储任务信息、状态和 Worker 信息
   - 使用 SQLite 数据库
   - 支持任务优先级、重试机制

2. **任务 Worker (TaskWorker)**
   - 从数据库队列中获取任务
   - 执行任务并更新进度
   - 与心跳进程协作

3. **心跳监控 (HeartbeatMonitor)**
   - 监控 Worker 健康状态
   - 检测超时的 Worker 和任务
   - 自动清理和恢复

### 工作流程

```
┌─────────────┐
│  创建任务    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  任务入队    │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│  Worker     │◄────►│  心跳监控    │
│  获取任务    │      │  监控健康    │
└──────┬──────┘      └─────────────┘
       │
       ▼
┌─────────────┐
│  执行任务    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  更新进度    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  完成任务    │
└─────────────┘
```

## 数据库设计

### tasks 表

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | TEXT | 任务 ID（主键） |
| task_type | TEXT | 任务类型 |
| task_name | TEXT | 任务名称 |
| status | TEXT | 任务状态 |
| priority | INTEGER | 优先级（1-4） |
| worker_id | TEXT | 执行任务的 Worker ID |
| created_at | TEXT | 创建时间 |
| queued_at | TEXT | 入队时间 |
| started_at | TEXT | 开始时间 |
| completed_at | TEXT | 完成时间 |
| duration | REAL | 执行时长（秒） |
| progress | INTEGER | 进度（0-100） |
| message | TEXT | 进度消息 |
| result | TEXT | 任务结果（JSON） |
| error | TEXT | 错误信息 |
| retry_count | INTEGER | 重试次数 |
| max_retries | INTEGER | 最大重试次数 |
| metadata | TEXT | 元数据（JSON） |
| updated_at | TEXT | 更新时间 |

### workers 表

| 字段 | 类型 | 说明 |
|------|------|------|
| worker_id | TEXT | Worker ID（主键） |
| worker_name | TEXT | Worker 名称 |
| status | TEXT | Worker 状态（idle/busy） |
| current_task_id | TEXT | 当前执行的任务 ID |
| last_heartbeat | TEXT | 最后心跳时间 |
| started_at | TEXT | Worker 启动时间 |
| completed_tasks | INTEGER | 完成的任务数 |
| failed_tasks | INTEGER | 失败的任务数 |
| metadata | TEXT | 元数据（JSON） |

## 任务状态

- **PENDING**: 等待处理（已创建但未入队）
- **QUEUED**: 已入队，等待 Worker 获取
- **RUNNING**: 正在执行
- **COMPLETED**: 已完成
- **FAILED**: 失败（超过最大重试次数）
- **CANCELLED**: 已取消
- **RETRYING**: 重试中

## 任务优先级

- **LOW (1)**: 低优先级
- **NORMAL (2)**: 普通优先级（默认）
- **HIGH (3)**: 高优先级
- **URGENT (4)**: 紧急优先级

## Worker 与心跳协作机制

### 1. Worker 注册和心跳

- Worker 启动时自动注册到数据库
- Worker 定期更新心跳（默认 30 秒）
- 心跳监控器监控所有 Worker 的健康状态

### 2. 任务获取和执行

- Worker 定期轮询数据库（默认 5 秒）
- 按优先级和创建时间排序获取任务
- 使用数据库事务确保只有一个 Worker 能获取任务

### 3. 健康监控和恢复

- 心跳监控器每 10 次心跳检查一次 Worker 健康状态
- 如果 Worker 超过 120 秒未更新心跳，认为 Worker 已崩溃
- 自动将超时的运行中任务重新入队

### 4. 任务重试机制

- 任务执行失败时，如果未超过最大重试次数，自动重试
- 重试任务重新入队，等待 Worker 获取
- 超过最大重试次数后，标记为失败

## API 接口

### 创建任务

```http
POST /api/task-queue/tasks
Content-Type: application/json

{
  "task_type": "video_process",
  "task_name": "处理视频文件",
  "priority": 3,
  "max_retries": 3,
  "metadata": {
    "video_path": "/path/to/video.mp4"
  },
  "auto_queue": true
}
```

### 获取任务

```http
GET /api/task-queue/tasks/{task_id}
```

### 列出任务

```http
GET /api/task-queue/tasks?status=running&limit=50&offset=0
```

### 取消任务

```http
POST /api/task-queue/tasks/{task_id}/cancel
```

### 列出 Worker

```http
GET /api/task-queue/workers
```

### 清理超时任务

```http
POST /api/task-queue/cleanup?max_idle_minutes=30
```

## 使用示例

### 1. 注册任务处理器

```python
from backend.infrastructure.execution.task_worker import get_task_worker

worker = get_task_worker()

async def process_video(task_info):
    """处理视频任务"""
    task_id = task_info["task_id"]
    metadata = task_info["metadata"]
    video_path = metadata.get("video_path")
    
    # 更新进度
    worker.update_task_progress(10, "开始处理视频")
    
    # 执行任务...
    result = await process_video_file(video_path)
    
    # 更新进度
    worker.update_task_progress(100, "视频处理完成")
    
    return result

# 注册处理器
worker.register_handler("video_process", process_video)
```

### 2. 创建任务

```python
from backend.infrastructure.storage.task_queue_db import (
    get_task_queue_db,
    TaskPriority
)

task_queue_db = get_task_queue_db()

# 创建任务
task_id = task_queue_db.create_task(
    task_type="video_process",
    task_name="处理视频文件",
    priority=TaskPriority.HIGH,
    max_retries=3,
    metadata={"video_path": "/path/to/video.mp4"}
)

# 入队
task_queue_db.queue_task(task_id)
```

### 3. 通过 API 创建任务

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8080/api/task-queue/tasks",
        json={
            "task_type": "video_process",
            "task_name": "处理视频文件",
            "priority": 3,
            "metadata": {"video_path": "/path/to/video.mp4"}
        }
    )
    result = response.json()
    task_id = result["task_id"]
```

## 配置

### 环境变量

- `TASK_WORKER_ENABLED`: 是否启用 Worker（默认 `true`）
- `TASK_WORKER_POLL_INTERVAL`: Worker 轮询间隔（秒，默认 `5`）
- `TASK_WORKER_HEARTBEAT_INTERVAL`: Worker 心跳间隔（秒，默认 `30`）

### 启动 Worker

Worker 会在后端服务启动时自动启动（如果启用）。也可以手动启动：

```python
from backend.infrastructure.execution.task_worker import get_task_worker

worker = get_task_worker()
await worker.start()
```

## 监控和调试

### 查看 Worker 状态

```python
worker = get_task_worker()
status = worker.get_status()
print(status)
```

### 查看任务队列

```python
task_queue_db = get_task_queue_db()
tasks = task_queue_db.list_tasks(status=TaskStatus.RUNNING)
workers = task_queue_db.list_workers()
```

### 清理超时任务

```python
task_queue_db = get_task_queue_db()
count = task_queue_db.cleanup_stale_tasks(max_idle_minutes=30)
print(f"清理了 {count} 个超时任务")
```

## 最佳实践

1. **任务类型命名**: 使用清晰的任务类型名称，如 `video_process`、`file_upload` 等
2. **优先级设置**: 合理设置任务优先级，避免所有任务都是高优先级
3. **重试次数**: 根据任务特性设置合理的重试次数
4. **错误处理**: 在任务处理器中妥善处理异常，提供有意义的错误信息
5. **进度更新**: 对于长时间运行的任务，定期更新进度
6. **资源清理**: 任务完成后及时清理资源

## 故障恢复

### Worker 崩溃

- 心跳监控器检测到 Worker 超时
- 自动将 Worker 正在执行的任务重新入队
- 其他 Worker 可以获取并执行这些任务

### 数据库锁定

- 使用 SQLite 的 `BEGIN IMMEDIATE` 确保事务隔离
- Worker 获取任务时使用事务锁定，避免并发问题

### 任务失败

- 自动重试机制（可配置最大重试次数）
- 超过最大重试次数后标记为失败
- 可以通过 API 查看失败原因

## 扩展性

### 多 Worker 支持

- 系统支持多个 Worker 同时运行
- 每个 Worker 独立注册和心跳
- 任务自动分配给可用的 Worker

### 任务类型扩展

- 通过 `register_handler` 注册新的任务类型处理器
- 支持任意类型的任务处理逻辑

### 监控集成

- 可以集成到现有的监控系统
- 提供详细的 Worker 和任务统计信息
