# 文件快速搜索服务

高性能的文件快速搜索功能，支持文件名搜索和文件内容搜索。

## 功能特性

- ✅ **文件名搜索**：支持通配符和正则表达式
- ✅ **文件内容搜索**：利用系统索引进行全文搜索
- ✅ **路径限制**：支持指定搜索目录
- ✅ **文件类型过滤**：按扩展名过滤结果
- ✅ **结果排序**：按文件名、大小、修改时间排序
- ✅ **分页支持**：支持 limit 和 offset 参数
- ✅ **结果缓存**：内存缓存，提升重复查询性能
- ✅ **并发搜索**：支持多个搜索任务并发执行
- ✅ **统计信息**：记录搜索耗时、结果数等统计信息

## 平台支持

- ✅ **macOS**：使用 `mdfind` 命令和 Spotlight 索引
- ⏳ **Linux**：计划支持（使用 `locate/plocate`）
- ⏳ **Windows**：计划支持（使用 Windows Search API）

## 快速开始

### 基本使用

```python
from backend.services.file_search_service import FileSearchService, FileSearchRequest

# 创建搜索服务
service = FileSearchService()

# 搜索 .py 文件
request = FileSearchRequest(
    query="*.py",
    limit=10
)
response = service.search(request)

# 查看结果
print(f"找到 {response.total} 个文件")
for result in response.results:
    print(f"- {result.name} ({result.size} bytes)")
```

### 带路径限制的搜索

```python
request = FileSearchRequest(
    query="*.py",
    path="/Users/username/project",
    limit=10
)
response = service.search(request)
```

### 文件内容搜索

```python
request = FileSearchRequest(
    query="TODO",
    content_search=True,
    limit=10
)
response = service.search(request)
```

### 文件类型过滤

```python
request = FileSearchRequest(
    query="test",
    file_type="*.py",
    limit=10
)
response = service.search(request)
```

### 结果排序

```python
request = FileSearchRequest(
    query="*.py",
    sort_by="size",
    sort_order="desc",
    limit=10
)
response = service.search(request)
```

### 分页

```python
# 第一页
request1 = FileSearchRequest(query="*.py", limit=10, offset=0)
response1 = service.search(request1)

# 第二页
request2 = FileSearchRequest(query="*.py", limit=10, offset=10)
response2 = service.search(request2)
```

### 并发搜索

```python
requests = [
    FileSearchRequest(query="*.py", limit=10),
    FileSearchRequest(query="*.md", limit=10),
    FileSearchRequest(query="*.txt", limit=10),
]

responses = service.search_concurrent(requests, max_workers=3)
for response in responses:
    print(f"找到 {response.total} 个文件")
```

## 查询构建器

使用 `QueryBuilder` 构建复杂的查询条件：

```python
from backend.services.file_search_service import QueryBuilder
from datetime import datetime, timedelta

# 构建复杂查询
builder = QueryBuilder()
query = (
    builder
    .name_contains("test")
    .file_type(".py")
    .size_greater_than(1024)
    .modified_in_last_days(7)
    .build()
)

# 使用查询字符串（需要适配器支持）
# 注意：当前 macOS 适配器使用 -name 参数，不支持复杂查询字符串
# 查询构建器主要用于未来支持复杂查询的平台
```

## API 接口

### REST API

```
GET /api/search/files
```

**查询参数**：
- `query` (必需): 搜索关键词
- `path` (可选): 搜索路径限制
- `file_type` (可选): 文件类型过滤（如 `*.py`）
- `content_search` (可选): 是否进行文件内容搜索（默认 `false`）
- `limit` (可选): 结果数量限制（默认 100，最大 1000）
- `offset` (可选): 分页偏移量（默认 0）
- `sort_by` (可选): 排序字段（`name`, `size`, `modified_time`）
- `sort_order` (可选): 排序顺序（`asc`, `desc`，默认 `asc`）

**响应示例**：
```json
{
  "results": [
    {
      "path": "/path/to/file.py",
      "name": "file.py",
      "size": 1024,
      "modified_time": "2024-01-01T00:00:00",
      "file_type": ".py"
    }
  ],
  "total": 100,
  "limit": 10,
  "offset": 0,
  "has_more": true,
  "search_time_ms": 123.45,
  "search_type": "name",
  "platform": "macos",
  "query_summary": "query='*.py', limit=10, offset=0"
}
```

## 缓存配置

```python
# 启用缓存（默认）
service = FileSearchService(cache_enabled=True, cache_ttl=300)

# 禁用缓存
service = FileSearchService(cache_enabled=False)

# 自定义缓存 TTL（秒）
service = FileSearchService(cache_enabled=True, cache_ttl=600)  # 10 分钟
```

## 性能优化

### 缓存

搜索服务默认启用缓存，缓存 TTL 为 5 分钟。重复查询相同条件时，会直接返回缓存结果，大幅提升性能。

### 并发搜索

对于需要同时执行多个搜索的场景，使用 `search_concurrent()` 方法可以并发执行，提升整体性能。

```python
responses = service.search_concurrent(requests, max_workers=5)
```

## 错误处理

### macOS 平台

如果 `mdfind` 命令不可用或 Spotlight 索引异常，会抛出 `RuntimeError` 并提供修复指导：

```python
try:
    service = FileSearchService()
except RuntimeError as e:
    print(f"搜索服务不可用: {e}")
    # 错误信息会包含修复步骤
```

**常见问题**：
1. **Spotlight 未启用**：前往"系统偏好设置" > "Spotlight" 启用
2. **Spotlight 正在索引**：等待索引完成
3. **权限问题**：确保有访问目标目录的权限

## 测试

运行单元测试：

```bash
python -m pytest backend/services/file_search_service/tests/
```

运行特定测试：

```bash
python -m pytest backend/services/file_search_service/tests/test_macos_search.py
python -m pytest backend/services/file_search_service/tests/test_query_builder.py
python -m pytest backend/services/file_search_service/tests/test_integration.py
python -m pytest backend/services/file_search_service/tests/test_performance.py
```

## 架构设计

```
FileSearchService (统一搜索服务)
    ↓
PlatformAdapter (平台适配器)
    ├── MacOSSearchAdapter (macOS 实现)
    ├── LinuxSearchAdapter (计划中)
    └── WindowsSearchAdapter (计划中)
```

## 数据模型

### FileSearchRequest

搜索请求模型，包含所有搜索参数。

### FileSearchResult

单个搜索结果，包含文件路径、名称、大小、修改时间等信息。

### FileSearchResponse

搜索响应，包含结果列表和统计信息。

## 开发计划

- [x] macOS 平台支持
- [ ] Linux 平台支持
- [ ] Windows 平台支持
- [ ] 复杂查询条件支持（使用查询构建器）
- [ ] 搜索结果高亮
- [ ] 文件内容预览

## 相关文档

- [设计文档](../../docs/design/06-文件快速搜索设计文档.md)
- [实现任务](../../docs/todo/009-macos-file-search-implementation.md)

