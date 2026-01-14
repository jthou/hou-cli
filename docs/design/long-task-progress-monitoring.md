# 长任务进度监控设计方案

## 问题描述

后端在执行长时间任务（如视频下载）时，没有向前端发送进度消息，导致前端认为任务超时（5分钟超时限制）。

## 设计方案：混合方案

采用 **后端主动发送进度（SSE）+ 前端异步任务管理** 的混合方案，既保证实时性，又支持在等待期间执行其他任务。

### 方案优势

1. **实时性好**：后端通过 SSE 主动推送进度，前端立即显示
2. **支持并发**：前端可以同时处理多个任务，在等待一个任务时可以执行其他任务
3. **容错性强**：即使 SSE 连接断开，前端也可以通过轮询查询任务状态
4. **用户体验好**：可以看到实时进度，不会因为超时中断

## 架构设计

### 1. 后端组件

#### 1.1 任务管理器 (`TaskManager`)
- 管理所有长时间运行的任务
- 跟踪任务状态（pending/running/completed/failed/cancelled）
- 存储任务进度和元数据
- 支持任务查询和取消

#### 1.2 长任务监控器 (`LongTaskMonitor`)
- 在长任务执行期间定时发送状态更新
- 自动计算已用时间和预计剩余时间
- 通过 SSE 推送进度到前端

#### 1.3 任务 API (`/api/tasks`)
- `GET /api/tasks/{task_id}` - 查询任务状态
- `GET /api/tasks` - 列出所有任务
- `POST /api/tasks/{task_id}/cancel` - 取消任务

### 2. 前端组件

#### 2.1 任务客户端 (`TaskClient`)
- 查询任务状态
- 列出所有任务
- 取消任务

#### 2.2 任务状态显示
- 实时显示任务进度条
- 显示已用时间和预计剩余时间
- 支持任务列表查看

## 工作流程

### 场景1：正常流程（SSE 推送）

```
1. 用户发起视频下载任务
2. 后端创建任务（TaskManager）
3. 后端启动长任务监控器（LongTaskMonitor）
4. 后端开始执行下载
5. 监控器每5秒发送一次进度更新（通过 SSE）
6. 前端实时显示进度
7. 任务完成，发送完成信号
```

### 场景2：SSE 连接断开（轮询备用）

```
1. SSE 连接断开
2. 前端检测到连接断开
3. 前端启动轮询任务（每5秒查询一次任务状态）
4. 继续显示进度
5. 任务完成后停止轮询
```

### 场景3：并发任务

```
1. 用户发起任务A（视频下载，长任务）
2. 前端显示任务A的进度，但保持可交互状态
3. 用户发起任务B（简单查询）
4. 前端立即处理任务B，同时继续显示任务A的进度
5. 两个任务可以并行执行
```

## 实现细节

### 后端实现

#### 1. 在 Orchestrator 中检测长任务

```python
# 检测是否是长任务
is_long_task = matched_skill.name in ['video_downloader']

if is_long_task:
    # 创建任务
    task_id = await task_manager.create_task(...)
    
    # 发送任务创建通知
    yield StreamMessageBuilder.build_status({
        "task": task_name,
        "progress": 0,
        "message": "任务已创建",
        "task_id": task_id
    })
```

#### 2. 在技能中更新进度

```python
# 在 video_downloader_skill 中
def progress_callback(progress: int, message: str = ""):
    if task_manager and task_id:
        task_manager.update_task_progress(task_id, progress, message)
```

#### 3. 定期发送状态更新

```python
# 使用 LongTaskMonitor
monitor = LongTaskMonitor(
    send_func=send_status_update,
    task_name="视频下载",
    update_interval=5.0
)
await monitor.start()
```

### 前端实现

#### 1. 接收状态更新

```python
# 在 stream_handler 中
elif msg_type == "status":
    self._render_status_info(msg_data, console)
```

#### 2. 轮询备用方案

```python
# 如果 SSE 断开，启动轮询
async def poll_task_status(task_id: str):
    while True:
        task = task_client.get_task(task_id)
        if task['status'] in ['completed', 'failed', 'cancelled']:
            break
        await asyncio.sleep(5)
```

## 配置选项

### 后端配置

- `LONG_TASK_UPDATE_INTERVAL`: 状态更新间隔（默认 5 秒）
- `TASK_CLEANUP_HOURS`: 任务清理时间（默认 24 小时）

### 前端配置

- `POLL_INTERVAL`: 轮询间隔（默认 5 秒）
- `SSE_TIMEOUT`: SSE 超时时间（默认 300 秒）

## 扩展性

### 支持更多长任务类型

只需在 `orchestrator.py` 中添加：

```python
is_long_task = matched_skill.name in [
    'video_downloader',
    'file_processing',
    'data_export',
    # ... 更多任务类型
]
```

### 自定义进度更新频率

不同任务可以设置不同的更新间隔：

```python
update_interval = {
    'video_downloader': 5.0,
    'file_processing': 2.0,
    'data_export': 10.0
}.get(matched_skill.name, 5.0)
```

## 总结

这个混合方案结合了两种方案的优点：
- **实时性**：通过 SSE 主动推送，保证实时性
- **灵活性**：支持并发任务，可以在等待期间执行其他任务
- **容错性**：轮询作为备用方案，即使 SSE 断开也能继续工作
- **可扩展性**：易于添加新的长任务类型

