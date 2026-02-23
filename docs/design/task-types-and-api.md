# 任务类型和API设计文档

## 后端任务类型

系统目前支持以下9种任务类型：

### 1. 文件处理 (file_process)
- **名称**: 文件处理
- **描述**: 处理文件操作任务（上传、下载、转换等）
- **元数据参数**:
  - `file_path` (string, 必需): 文件路径
  - `operation` (string, 必需): 操作类型（upload/download/convert）

### 2. 数据导出 (data_export)
- **名称**: 数据导出
- **描述**: 导出数据到文件（CSV、JSON、Excel等）
- **元数据参数**:
  - `data_source` (string, 必需): 数据源
  - `format` (string, 必需): 导出格式（csv/json/excel）
  - `output_path` (string, 必需): 输出路径

### 3. 数据导入 (data_import)
- **名称**: 数据导入
- **描述**: 从文件导入数据到系统
- **元数据参数**:
  - `file_path` (string, 必需): 文件路径
  - `format` (string, 必需): 文件格式（csv/json/excel）

### 4. 批量处理 (batch_process)
- **名称**: 批量处理
- **描述**: 批量处理多个任务
- **元数据参数**:
  - `items` (array, 必需): 待处理项目列表
  - `operation` (string, 必需): 处理操作

### 5. 定时任务 (scheduled_task)
- **名称**: 定时任务
- **描述**: 定时执行的任务
- **元数据参数**:
  - `schedule_time` (string, 必需): 执行时间（ISO格式）
  - `action` (string, 必需): 要执行的操作

### 6. 数据备份 (backup)
- **名称**: 数据备份
- **描述**: 备份系统数据
- **元数据参数**:
  - `backup_type` (string, 必需): 备份类型（full/incremental）
  - `target_path` (string, 必需): 备份目标路径

### 7. 清理任务 (cleanup)
- **名称**: 清理任务
- **描述**: 清理临时文件、过期数据等
- **元数据参数**:
  - `cleanup_type` (string, 必需): 清理类型（temp_files/old_data/cache）
  - `retention_days` (integer, 可选): 保留天数

### 8. 报告生成 (report_generation)
- **名称**: 报告生成
- **描述**: 生成各种报告
- **元数据参数**:
  - `report_type` (string, 必需): 报告类型
  - `format` (string, 必需): 报告格式（pdf/html）
  - `output_path` (string, 必需): 输出路径

### 9. 自定义任务 (custom)
- **名称**: 自定义任务
- **描述**: 用户自定义的任务类型
- **元数据参数**:
  - `action` (string, 必需): 自定义操作
  - `params` (object, 可选): 自定义参数

## API设计

### 1. 获取任务类型列表

**端点**: `GET /api/task-queue/task-types`

**响应**:
```json
{
  "success": true,
  "task_types": [
    {
      "type": "file_process",
      "name": "文件处理",
      "description": "处理文件操作任务（上传、下载、转换等）",
      "metadata_schema": {
        "file_path": {
          "type": "string",
          "required": true,
          "description": "文件路径"
        },
        "operation": {
          "type": "string",
          "required": true,
          "description": "操作类型（upload/download/convert）"
        }
      }
    },
    ...
  ],
  "count": 9
}
```

### 2. 获取特定任务类型信息

**端点**: `GET /api/task-queue/task-types/{task_type}`

**响应**:
```json
{
  "success": true,
  "task_type": {
    "type": "file_process",
    "name": "文件处理",
    "description": "处理文件操作任务（上传、下载、转换等）",
    "metadata_schema": {
      "file_path": {
        "type": "string",
        "required": true,
        "description": "文件路径"
      },
      "operation": {
        "type": "string",
        "required": true,
        "description": "操作类型（upload/download/convert）"
      }
    }
  }
}
```

### 3. 创建任务

**端点**: `POST /api/task-queue/tasks`

**请求体**:
```json
{
  "task_type": "file_process",
  "task_name": "处理视频文件",
  "priority": 2,
  "max_retries": 3,
  "metadata": {
    "file_path": "/path/to/video.mp4",
    "operation": "convert"
  },
  "auto_queue": true
}
```

**响应**:
```json
{
  "success": true,
  "task_id": "task-1234567890-abc",
  "message": "任务已创建并已入队"
}
```

### 4. 其他任务管理API

- `GET /api/task-queue/tasks` - 列出任务
- `GET /api/task-queue/tasks/{task_id}` - 获取任务详情
- `POST /api/task-queue/tasks/{task_id}/queue` - 将任务加入队列
- `POST /api/task-queue/tasks/{task_id}/cancel` - 取消任务
- `GET /api/task-queue/workers` - 列出所有 Worker
- `POST /api/task-queue/cleanup` - 清理超时任务

## 前端体现

### 1. 任务类型选择

前端通过调用 `GET /api/task-queue/task-types` 获取可用任务类型列表，在创建任务时显示：

- **下拉选择框**: 显示所有可用任务类型及其描述
- **动态表单**: 根据选择的任务类型，动态生成相应的元数据输入字段
- **表单验证**: 根据元数据schema验证必填字段

### 2. 创建任务界面

创建任务时，前端提供以下功能：

1. **任务类型选择**: 下拉菜单显示所有可用任务类型
2. **任务名称输入**: 文本输入框
3. **优先级选择**: 下拉菜单（1-4）
4. **最大重试次数**: 数字输入框
5. **自动入队选项**: 复选框
6. **动态元数据字段**: 根据任务类型自动生成相应的输入字段

### 3. 任务列表展示

任务列表页面显示：

- **任务统计**: 总任务数、待处理、运行中、已完成、失败
- **任务过滤**: 按状态过滤
- **任务搜索**: 按任务名称或ID搜索
- **任务详情**: 点击查看任务详细信息
- **任务操作**: 取消运行中的任务、清理超时任务

### 4. 任务详情展示

任务详情包括：

- 任务基本信息（ID、名称、类型、状态）
- 任务时间信息（创建、开始、完成时间）
- 任务进度（进度条和百分比）
- 任务元数据（JSON格式显示）
- 任务结果或错误信息

## 扩展任务类型

要添加新的任务类型：

1. **在 `task_handlers.py` 中添加任务类型定义**:
```python
TASK_TYPES["new_task_type"] = {
    "name": "新任务类型",
    "description": "任务描述",
    "metadata_schema": {
        "param1": {"type": "string", "required": True, "description": "参数1"}
    }
}
```

2. **实现任务处理器函数**:
```python
async def process_new_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    # 实现任务处理逻辑
    pass
```

3. **注册任务处理器**:
```python
def register_default_handlers():
    worker = get_task_worker()
    worker.register_handler("new_task_type", process_new_task)
```

4. **前端会自动识别新任务类型**（无需修改前端代码）

## 使用示例

### 创建文件处理任务

```javascript
// 前端代码
const taskData = {
    task_type: "file_process",
    task_name: "转换视频文件",
    priority: 2,
    max_retries: 3,
    metadata: {
        file_path: "/path/to/video.mp4",
        operation: "convert"
    },
    auto_queue: true
};

const response = await fetch('/api/task-queue/tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(taskData)
});
```

### 创建批量处理任务

```javascript
const taskData = {
    task_type: "batch_process",
    task_name: "批量处理100个文件",
    priority: 3,
    metadata: {
        items: ["file1.txt", "file2.txt", "file3.txt"],
        operation: "process"
    },
    auto_queue: true
};
```

## 总结

- **后端**: 定义了9种任务类型，每种类型都有对应的处理器和元数据schema
- **API**: 提供了完整的任务管理API，包括获取任务类型、创建任务、管理任务等
- **前端**: 动态展示任务类型，根据类型生成表单，提供完整的任务管理界面

系统设计具有良好的扩展性，可以轻松添加新的任务类型而无需修改前端代码。
