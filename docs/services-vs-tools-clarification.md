# Services vs Tools 澄清文档

## 问题

`google_search_service` 和 `file_search_service` 是给 LLM 提供能力的，它们应该是 Services 还是 Tools？

## 答案：它们都是 Services

### 核心区别

| 维度 | Services | Tools |
|------|----------|-------|
| **定位** | 底层服务实现 | Agent/LLM 使用的接口层 |
| **职责** | API 客户端、业务逻辑、数据处理 | 封装 Services，符合 Tool 接口规范 |
| **使用场景** | 可被多个地方复用（Tools、API、其他服务） | 专门给 Agent/LLM 使用（Function Calling） |
| **接口** | 自定义接口（Service 类的方法） | 标准化接口（Tool 基类的 execute 方法） |
| **位置** | `backend/services/` | `backend/core/tools/`（推荐）或 `backend/core/agent/tools/`（当前） |

## 实际例子

### GoogleSearchService（Service）

**位置**：`backend/services/google_search_service/client.py`

**职责**：
- 封装 Google Custom Search API
- 处理 API 请求和响应
- 错误处理和重试逻辑
- 数据模型定义

**代码示例**：
```python
class GoogleSearchService:
    """Google Custom Search API 服务"""
    
    async def search(self, query: str, num_results: int = 5):
        """执行搜索，返回原始搜索结果"""
        # API 调用逻辑
        ...
```

**特点**：
- ✅ 可被多个地方复用（Tool、API 路由、其他服务）
- ✅ 不依赖 Agent 架构
- ✅ 提供底层能力

### GoogleSearchTool（Tool）

**位置**：`backend/core/agent/tools/builtin/google_search_tool.py`

**职责**：
- 封装 GoogleSearchService
- 实现 Tool 接口（继承 Tool 基类）
- 参数验证和格式化
- 结果转换为 ToolResult 格式
- 提供给 LLM 使用（Function Calling）

**代码示例**：
```python
class GoogleSearchTool(Tool):
    """Google 搜索工具 - 给 LLM 使用"""
    
    def __init__(self):
        super().__init__(
            name="google_search",
            description="使用 Google 搜索获取网络信息",
            parameters=[...]
        )
        self._search_service: Optional[GoogleSearchService] = None
    
    def execute(self, **kwargs) -> ToolResult:
        """执行搜索，返回 ToolResult"""
        service = self._get_search_service()
        results = service.search(...)  # 使用 Service
        return ToolResult(success=True, data=results)
```

**特点**：
- ✅ 专门给 Agent/LLM 使用
- ✅ 符合 Tool 接口规范
- ✅ 依赖 Services

## 关系图

```
┌─────────────────────────────────────┐
│         Agent / LLM                  │
│    (使用 Function Calling)           │
└──────────────┬──────────────────────┘
               │ 调用
               ▼
┌─────────────────────────────────────┐
│         Tools (工具层)               │
│  - GoogleSearchTool                 │
│  - FileSearchTool                   │
│  - WikipediaTool                    │
│  (实现 Tool 接口，封装 Services)     │
└──────────────┬──────────────────────┘
               │ 使用
               ▼
┌─────────────────────────────────────┐
│      Services (服务层)              │
│  - GoogleSearchService              │
│  - FileSearchService                │
│  - WikipediaService                 │
│  (底层 API 客户端、业务逻辑)         │
└─────────────────────────────────────┘
```

## 为什么这样设计？

### 1. 职责分离

- **Services**：专注于底层实现（API 调用、数据处理）
- **Tools**：专注于 Agent 接口（Function Calling、参数验证）

### 2. 可复用性

- **Services** 可以被多个地方使用：
  - Tools（如 GoogleSearchTool）
  - API 路由（如 `/api/search/google`）
  - 其他服务（如某个分析服务需要搜索功能）

### 3. 测试和维护

- **Services** 可以独立测试（不依赖 Agent 架构）
- **Tools** 可以独立测试（Mock Services）

## 结论

**`google_search_service` 和 `file_search_service` 应该保持在 `services/` 目录下**，因为：

1. ✅ 它们是底层服务实现（API 客户端、业务逻辑）
2. ✅ 可以被多个地方复用（不仅限于 Tools）
3. ✅ 不依赖 Agent 架构
4. ✅ 提供底层能力，而不是 Agent 接口

**对应的 Tools**（`google_search_tool`、`file_search_tool`）应该：
- 保持在 `backend/core/tools/`（推荐）或 `backend/core/agent/tools/`（当前）
- 使用 Services 来实现功能
- 提供给 Agent/LLM 使用

## 类比

- **Services** = 汽车的引擎（提供动力）
- **Tools** = 汽车的方向盘和踏板（给司机使用的接口）
- **Agent** = 司机（使用 Tools 来控制汽车）

引擎（Services）可以被多个地方使用（汽车、发电机等），但方向盘（Tools）是专门给司机（Agent）使用的接口。

