# 存储审计设计

## 概述

存储审计页面（`/settings/storage`）用于展示本项目所用到的存储：临时文件、输出文件、数据库、配置数据、系统文件等，便于磁盘清理和容量管理。

## 后端

### API

- **GET /api/storage/audit**：返回存储审计数据

### 数据结构

```json
{
  "success": true,
  "summary": {
    "total_bytes": 123456789,
    "human": "117.74 MB"
  },
  "app_data": {
    "path": "~/Library/Application Support/hou-cli",
    "size_bytes": 12345,
    "human": "12.06 KB",
    "subdirs": [
      {"name": "databases", "path": "...", "size_bytes": 1000, "human": "1.00 KB"},
      {"name": "chroma", "path": "...", "size_bytes": 2000, "human": "2.00 KB"},
      {"name": "tmp", "path": "...", "size_bytes": 3000, "human": "2.93 KB"}
    ]
  },
  "temp_root": { "path": "...", "size_bytes": 0, "human": "0 B" },
  "system_temp": {
    "base_path": "/tmp",
    "items": [
      {"name": "hou-cli-sandbox", "path": "...", "size_bytes": 0, "human": "0 B"},
      {"name": "hou-cli-pdf", "path": "...", "size_bytes": 0, "human": "0 B"}
    ]
  },
  "outputs": {
    "path": "~/hou-cli/outputs",
    "size_bytes": 0,
    "human": "0 B",
    "subdirs": [
      {"task_type": "video_download", "path": "...", "size_bytes": 0, "human": "0 B"}
    ]
  },
  "databases": {
    "dir": "...",
    "files": [{"name": "task_queue.db", "path": "...", "size_bytes": 1024, "human": "1.00 KB"}],
    "total_bytes": 1024
  },
  "config": {
    "files": [{"name": ".env", "path": "...", "size_bytes": 500, "human": "500 B"}]
  },
  "chromadb": {
    "path": "...",
    "size_bytes": 0,
    "human": "0 B",
    "collections": [{"name": "kb", "count": 10, "metadata": {}}]
  }
}
```

### 模块

- **shared/storage_audit.py**：`collect_storage_audit(project_root)` 收集审计数据
- **backend/api/storage_routes.py**：`GET /storage/audit` 端点

### 覆盖的存储类型

| 类型 | 路径/说明 |
|------|-----------|
| 应用数据 | `get_app_data_dir()`（含 databases、chroma、tmp） |
| 临时根 | `get_temp_root_dir()` |
| 系统临时 | `tempfile.gettempdir()` 下的 hou-cli-sandbox、hou-cli-pdf |
| 输出 | `~/hou-cli/outputs` 及按任务类型子目录 |
| 数据库 | `databases/*.db` |
| 配置 | `.env`、`port.txt` |
| ChromaDB | 向量库目录及集合列表 |

## 前端

### 页面

- **路径**：`/settings/storage`
- **组件**：`frontend/react-app/src/pages/SettingsStorage.jsx`
- **标签**：存储审计（默认）、存储配置

### 存储审计 Tab

- 汇总：总大小
- 应用数据目录：路径、大小、子目录
- 临时文件：项目临时根、系统临时子目录
- 输出文件：输出根、按任务类型子目录
- 数据库：目录、文件列表及大小
- 配置数据：配置文件列表
- Chroma 向量库：路径、大小、集合列表

## 测试

- **backend/api/tests/test_storage_routes.py**：API 单元测试（含 audit 成功/失败）
- **shared/tests/test_storage_audit.py**：`collect_storage_audit` 单元测试

### 集成测试

1. 启动服务：`make start` 或 `python cli.py start`
2. 访问：http://127.0.0.1:8081/settings/storage
3. 验证：存储审计 Tab 显示汇总及各分类数据
