# 心跳机制实现文档

## 概述

心跳机制用于监控后端服务的健康状态，包括：
- **后端心跳监控**：定期收集系统指标（CPU、内存等）
- **前端健康检查**：定期检查后端服务是否可用
- **自动恢复**：检测到后端不可用时触发恢复机制

## 架构设计

```
┌─────────────────────────────────────────┐
│           后端服务 (Backend)             │
│  ┌───────────────────────────────────┐  │
│  │  HeartbeatMonitor                 │  │
│  │  - 每 30 秒收集系统指标            │  │
│  │  - 记录 CPU、内存使用率            │  │
│  │  - 提供状态查询接口                │  │
│  └───────────────────────────────────┘  │
│           │                               │
│           │ HTTP GET /health              │
│           │ HTTP GET /api/heartbeat/status│
│           ▼                               │
└─────────────────────────────────────────┘
           │
           │ HTTP 请求
           ▼
┌─────────────────────────────────────────┐
│           前端服务 (Frontend)            │
│  ┌───────────────────────────────────┐  │
│  │  HealthMonitor                    │  │
│  │  - 每 30 秒检查后端健康状态         │  │
│  │  - 连续失败 3 次触发回调            │  │
│  │  - 支持自动恢复机制                 │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## 后端实现

### 1. 心跳监控器 (`backend/infrastructure/monitoring/heartbeat.py`)

**功能**：
- 定期收集系统指标（CPU、内存、运行时间）
- 记录心跳时间戳
- 提供健康状态查询

**使用方式**：

```python
from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor

# 获取监控器（单例）
monitor = get_heartbeat_monitor(interval=30)  # 30 秒间隔

# 启动监控
await monitor.start()

# 获取状态
status = monitor.get_status()
# {
#     "is_running": True,
#     "last_heartbeat": "2025-02-17T10:30:00",
#     "heartbeat_count": 100,
#     "uptime_seconds": 3000,
#     "metrics": {
#         "cpu_percent": 15.5,
#         "memory_percent": 45.2,
#         "memory_used_mb": 1024.5,
#         "uptime_seconds": 3000
#     }
# }

# 检查是否健康
is_healthy = monitor.is_healthy(max_silence_seconds=60)

# 停止监控
await monitor.stop()
```

### 2. 自动启动（已在 `backend/main.py` 中集成）

后端服务启动时自动启动心跳监控：

```python
@app.on_event("startup")
async def startup_event():
    # ... 其他初始化代码 ...
    
    # 启动心跳监控
    from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
    heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
    heartbeat_monitor = get_heartbeat_monitor(interval=heartbeat_interval)
    await heartbeat_monitor.start()
```

### 3. API 端点

**健康检查端点**：
```
GET /health
```

响应：
```json
{
    "status": "ok",
    "service": "hou-cli-backend",
    "heartbeat": {
        "is_running": true,
        "last_heartbeat": "2025-02-17T10:30:00",
        "heartbeat_count": 100,
        "metrics": {...}
    }
}
```

**心跳状态端点**：
```
GET /api/heartbeat/status
```

响应：
```json
{
    "success": true,
    "status": {
        "is_running": true,
        "last_heartbeat": "2025-02-17T10:30:00",
        "heartbeat_count": 100,
        "metrics": {...}
    }
}
```

## 前端实现

### 1. 健康监控器 (`frontend/client/health_monitor.py`)

**功能**：
- 定期检查后端健康状态
- 记录检查统计信息
- 支持回调函数（后端不可用时触发）

**使用方式**：

```python
from frontend.client.health_monitor import HealthMonitor

# 创建监控器
monitor = HealthMonitor(
    base_url="http://127.0.0.1:8000",
    interval=30,           # 30 秒检查一次
    timeout=5.0,           # 5 秒超时
    max_failures=3         # 连续失败 3 次触发回调
)

# 设置回调函数
async def on_unhealthy():
    """后端不可用时的回调"""
    print("后端服务不可用，尝试重启...")
    # 可以在这里实现自动重启逻辑

async def on_recovered():
    """后端恢复时的回调"""
    print("后端服务已恢复")

monitor.set_callbacks(
    on_unhealthy=on_unhealthy,
    on_recovered=on_recovered
)

# 启动监控
await monitor.start()

# 获取状态
status = monitor.get_status()
# {
#     "is_running": true,
#     "last_check": "2025-02-17T10:30:00",
#     "last_success": "2025-02-17T10:30:00",
#     "consecutive_failures": 0,
#     "total_checks": 100,
#     "total_failures": 2,
#     "success_rate": 98.0,
#     "is_healthy": true
# }

# 停止监控
await monitor.stop()
```

### 2. 集成到前端主程序

在 `frontend/main.py` 中集成：

```python
from frontend.client.health_monitor import HealthMonitor

async def chat_main():
    # 创建 IPC 客户端
    client = IPCClient()
    
    # 创建健康监控器
    monitor = HealthMonitor(
        base_url=client.base_url,
        interval=30,
        max_failures=3
    )
    
    # 设置回调
    async def on_unhealthy():
        console.print("[yellow]⚠ 后端服务不可用，尝试重新连接...[/yellow]")
        # 可以在这里实现重连逻辑
    
    monitor.set_callbacks(on_unhealthy=on_unhealthy)
    
    # 启动监控
    await monitor.start()
    
    try:
        # 主循环
        while True:
            # ... 聊天逻辑 ...
            pass
    finally:
        # 停止监控
        await monitor.stop()
```

## 配置

### 环境变量

**后端配置**：
```bash
# .env 文件
HEARTBEAT_INTERVAL=30  # 心跳间隔（秒），默认 30
```

**前端配置**（可选）：
```python
# 代码中配置
monitor = HealthMonitor(
    interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
    timeout=float(os.getenv("HEALTH_CHECK_TIMEOUT", "5.0")),
    max_failures=int(os.getenv("HEALTH_CHECK_MAX_FAILURES", "3"))
)
```

## 监控指标

### 后端指标

- **CPU 使用率**：`metrics.cpu_percent`
- **内存使用率**：`metrics.memory_percent`
- **内存使用量**：`metrics.memory_used_mb` (MB)
- **运行时间**：`metrics.uptime_seconds` (秒)
- **心跳计数**：`heartbeat_count`
- **最后心跳时间**：`last_heartbeat`

### 前端指标

- **总检查次数**：`total_checks`
- **总失败次数**：`total_failures`
- **成功率**：`success_rate` (%)
- **连续失败次数**：`consecutive_failures`
- **最后检查时间**：`last_check`
- **最后成功时间**：`last_success`

## 最佳实践

### 1. 心跳间隔设置

- **开发环境**：30 秒（默认）
- **生产环境**：60 秒（减少资源占用）
- **高负载环境**：15 秒（更频繁检查）

### 2. 失败阈值

- **快速检测**：`max_failures=2`（更快发现问题）
- **稳定检测**：`max_failures=3`（默认，避免误报）
- **宽松检测**：`max_failures=5`（减少误报）

### 3. 超时设置

- **本地网络**：`timeout=2.0`（快速失败）
- **标准网络**：`timeout=5.0`（默认）
- **慢速网络**：`timeout=10.0`（容忍网络延迟）

### 4. 自动恢复策略

```python
async def on_unhealthy():
    """自动恢复策略"""
    console.print("[yellow]后端服务不可用，尝试恢复...[/yellow]")
    
    # 策略 1: 等待后重试
    await asyncio.sleep(5)
    if await monitor._check_health():
        console.print("[green]后端服务已恢复[/green]")
        return
    
    # 策略 2: 尝试重启后端
    console.print("[yellow]尝试重启后端服务...[/yellow]")
    # 调用重启逻辑
    # restart_backend()
```

## 故障排查

### 1. 心跳监控未启动

**检查**：
```python
from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
monitor = get_heartbeat_monitor()
print(monitor.get_status())
```

**解决**：
- 检查日志中是否有启动错误
- 确认 `psutil` 库已安装
- 检查环境变量 `HEARTBEAT_INTERVAL` 是否有效

### 2. 健康检查失败

**检查**：
```python
# 手动检查
import httpx
response = httpx.get("http://127.0.0.1:8000/health")
print(response.json())
```

**解决**：
- 确认后端服务正在运行
- 检查端口是否正确
- 检查防火墙设置

### 3. 指标异常

**检查**：
```python
status = monitor.get_status()
print(status["metrics"])
```

**解决**：
- CPU/内存过高：检查是否有资源泄漏
- 心跳计数不增加：检查监控任务是否运行
- 最后心跳时间过旧：检查监控任务是否卡住

## 总结

### 已实现功能

✅ 后端心跳监控（系统指标收集）
✅ 前端健康检查（定期检查后端状态）
✅ API 端点（健康检查和状态查询）
✅ 自动启动（后端启动时自动启动监控）

### 可选功能

- ⚠️ 自动恢复机制（需要根据需求实现）
- ⚠️ 告警通知（可以添加邮件/日志告警）
- ⚠️ 指标持久化（可以存储到数据库）

### 使用建议

1. **开发环境**：使用默认配置即可
2. **生产环境**：调整间隔和阈值，减少资源占用
3. **监控集成**：可以集成到监控系统（如 Prometheus）

