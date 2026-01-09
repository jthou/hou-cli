# 知乎直达（Zhihu Zhida）集成方案设计

## 概述

知乎直达（https://zhida.zhihu.com）是一个提问式的网页知识库，用户可以通过 URL 访问特定的问题和答案。本文档设计将其集成到 CLI 系统的方案。

## 知乎直达特点分析

### 1. URL 结构
- 格式：`https://zhida.zhihu.com/search/{search_id}`
- 示例：`https://zhida.zhihu.com/search/3707579171380201696`
- 每个 URL 对应一个特定的问题或搜索

### 2. 内容结构
- **问题标题**：页面的核心问题
- **问题描述**：问题的详细说明
- **答案列表**：多个用户提供的答案
- **元数据**：浏览量、点赞数、回答时间等

### 3. 访问要求
- 部分内容需要登录才能查看
- 完整答案可能需要登录
- 可以使用浏览器工具保存登录状态

## 集成方案

### 方案1：浏览器工具封装（简单快速）⭐ 推荐

**优点**：
- 实现简单，复用现有 browser 工具
- 无需额外依赖
- 支持登录状态管理

**缺点**：
- 每次都需要访问网页
- 无法离线使用
- 内容提取依赖页面结构

**实现方式**：
```python
# 用户请求
用户：获取知乎直达 https://zhida.zhihu.com/search/3707579171380201696 的内容

# AI 调用 browser 工具
browser(
    task="访问 https://zhida.zhihu.com/search/3707579171380201696 并提取问题和答案内容",
    user_data_dir="zhihu",
    headless=False
)
```

**适用场景**：
- 偶尔查询
- 需要最新内容
- 简单快速访问

---

### 方案2：专门的知乎直达工具（功能完整）⭐⭐⭐ 最佳

**优点**：
- 专门优化的工具，体验更好
- 支持内容提取和结构化
- 可以缓存内容
- 支持批量操作

**缺点**：
- 需要实现内容解析逻辑
- 需要处理页面结构变化

**实现方式**：
创建 `ZhihuZhidaTool`，类似 `MediaWikiTool`

**功能设计**：
```python
class ZhihuZhidaTool(Tool):
    """知乎直达工具
    
    支持：
    - 读取问题和答案
    - 搜索相关问题
    - 提取结构化内容
    - 保存到本地知识库（可选）
    """
    
    operations = [
        "read",      # 读取问题和答案
        "search",    # 搜索相关问题
        "extract",   # 提取结构化内容
        "save"       # 保存到知识库
    ]
```

**工具参数**：
- `url` 或 `search_id`: 知乎直达 URL 或搜索 ID
- `operation`: 操作类型（read/search/extract/save）
- `format`: 输出格式（markdown/json/text）
- `save_to_kb`: 是否保存到知识库

**使用示例**：
```
用户：读取知乎直达 https://zhida.zhihu.com/search/3707579171380201696

AI 调用：
zhihu_zhida(
    operation="read",
    url="https://zhida.zhihu.com/search/3707579171380201696",
    format="markdown"
)
```

---

### 方案3：知识库集成（长期存储）⭐⭐

**优点**：
- 内容本地化，支持离线查询
- 可以建立索引，支持语义搜索
- 支持批量导入
- 可以与其他知识库整合

**缺点**：
- 需要实现内容提取和存储
- 需要定期同步更新
- 占用存储空间

**实现方式**：
1. 使用 browser 工具访问并提取内容
2. 解析问题和答案
3. 存储到本地知识库（文件或向量数据库）
4. 建立索引支持搜索

**数据模型**：
```python
class ZhihuZhidaItem:
    search_id: str
    question_title: str
    question_content: str
    answers: List[Answer]
    metadata: Dict
    url: str
    saved_at: datetime
```

**存储位置**：
- `{app_data_dir}/knowledge/zhihu_zhida/`
- 支持 JSON 文件和向量数据库两种存储方式

---

### 方案4：混合方案（推荐）⭐⭐⭐⭐

**结合方案2和方案3的优势**：

1. **短期访问**：使用专门的工具快速读取
2. **长期存储**：可选保存到知识库
3. **智能缓存**：已保存的内容优先从本地读取
4. **增量更新**：定期检查更新

**工作流程**：
```
用户请求 → 检查本地缓存 → 
  ├─ 有缓存且未过期 → 返回本地内容
  └─ 无缓存或已过期 → 访问网页 → 提取内容 → 可选保存 → 返回内容
```

## 详细设计：方案2（专门工具）

### 工具类设计

```python
class ZhihuZhidaTool(Tool):
    """知乎直达工具"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="url",
                type="string",
                description="知乎直达 URL 或搜索 ID",
                required=True
            ),
            ToolParameter(
                name="operation",
                type="string",
                description="操作类型：'read'（读取）、'extract'（提取结构化）、'search'（搜索）",
                required=False,
                default="read",
                enum=["read", "extract", "search"]
            ),
            ToolParameter(
                name="format",
                type="string",
                description="输出格式：'markdown'、'json'、'text'",
                required=False,
                default="markdown",
                enum=["markdown", "json", "text"]
            ),
            ToolParameter(
                name="save_to_kb",
                type="boolean",
                description="是否保存到知识库（默认 false）",
                required=False,
                default=False
            ),
        ]
```

### 内容提取策略

**使用 browser-use 的 extract 功能**：
```python
# 在 browser 任务中使用 extract action
task = """
访问 {url}，然后：
1. 提取问题标题
2. 提取问题描述
3. 提取所有答案（包括作者、内容、点赞数）
4. 返回结构化数据
"""
```

**或使用自定义解析**：
- 使用 Playwright 的 DOM 选择器
- 解析 JSON-LD 结构化数据（如果有）
- 使用 LLM 提取结构化内容

### 缓存机制

```python
class ZhihuZhidaCache:
    """知乎直达缓存"""
    
    def __init__(self):
        from shared.platform_utils import get_app_data_dir
        self.cache_dir = get_app_data_dir() / "cache" / "zhihu_zhida"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, search_id: str) -> Optional[Dict]:
        """获取缓存内容"""
        cache_file = self.cache_dir / f"{search_id}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        return None
    
    def save(self, search_id: str, data: Dict):
        """保存缓存"""
        cache_file = self.cache_dir / f"{search_id}.json"
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
```

## 实现步骤

### 阶段1：基础工具（方案2）

1. **创建工具类**
   - 文件：`backend/core/agent/tools/builtin/zhihu_zhida_tool.py`
   - 实现基本的 read 操作
   - 使用 browser 工具访问并提取内容

2. **内容提取**
   - 使用 browser-use 的 extract action
   - 或使用 Playwright 的 DOM 解析

3. **格式化输出**
   - 支持 Markdown、JSON、Text 格式
   - 美化输出，便于阅读

### 阶段2：增强功能

1. **缓存机制**
   - 实现本地缓存
   - 支持缓存过期时间

2. **批量操作**
   - 支持批量读取多个 URL
   - 支持搜索相关问题和答案

3. **错误处理**
   - 处理登录要求
   - 处理页面结构变化
   - 处理网络错误

### 阶段3：知识库集成（方案3）

1. **存储模块**
   - 实现内容存储
   - 支持 JSON 文件和向量数据库

2. **索引建立**
   - 使用向量数据库建立索引
   - 支持语义搜索

3. **同步更新**
   - 定期检查内容更新
   - 增量同步

## 技术实现细节

### 1. 使用 Browser 工具

```python
async def _read_zhida_page(self, url: str) -> Dict:
    """读取知乎直达页面"""
    from backend.core.agent.tools.builtin.browser_tool import BrowserTool
    
    browser_tool = BrowserTool()
    task = f"""
    访问 {url}，然后使用 extract action 提取：
    1. 问题标题
    2. 问题描述
    3. 所有答案（包括作者、内容、点赞数、时间）
    返回 JSON 格式的结构化数据
    """
    
    result = await browser_tool._execute_async(
        task=task,
        user_data_dir="zhihu",
        headless=True
    )
    
    # 解析结果
    return self._parse_content(result)
```

### 2. 内容解析

```python
def _parse_content(self, browser_result: ToolResult) -> Dict:
    """解析浏览器返回的内容"""
    # 从 browser_result 中提取结构化数据
    # 可以使用正则表达式、JSON 解析或 LLM 提取
    pass
```

### 3. 格式化输出

```python
def _format_output(self, data: Dict, format: str) -> str:
    """格式化输出"""
    if format == "markdown":
        return self._to_markdown(data)
    elif format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    else:
        return self._to_text(data)
```

## 使用场景示例

### 场景1：快速查询

```
用户：知乎直达 https://zhida.zhihu.com/search/3707579171380201696 的内容是什么？

AI：使用 zhihu_zhida 工具读取内容
→ 返回格式化的问题和答案
```

### 场景2：批量导入

```
用户：将这些知乎直达 URL 保存到知识库：
1. https://zhida.zhihu.com/search/3707579171380201696
2. https://zhida.zhihu.com/search/1234567890123456789

AI：使用 zhihu_zhida 工具批量读取并保存
```

### 场景3：知识检索

```
用户：在知乎直达知识库中搜索"Python 异步编程"

AI：在本地知识库中搜索相关内容
```

## 推荐方案

**推荐使用方案4（混合方案）**，分阶段实现：

1. **第一阶段**：实现方案2（专门工具）
   - 快速实现基本功能
   - 支持读取和提取
   - 支持格式化输出

2. **第二阶段**：添加缓存机制
   - 提高访问速度
   - 减少网络请求

3. **第三阶段**：集成知识库
   - 支持长期存储
   - 支持语义搜索
   - 支持批量管理

## 与现有系统的集成点

1. **浏览器工具**：复用现有的 browser 工具和会话管理
2. **知识库基础设施**：使用 `backend/infrastructure/knowledge/` 中的模块
3. **工具注册**：在 `orchestrator.py` 中注册新工具
4. **配置目录**：使用统一的 `get_app_data_dir()` 管理数据

## 注意事项

1. **登录状态**：需要确保浏览器工具已登录知乎
2. **页面结构**：知乎页面结构可能变化，需要健壮的错误处理
3. **内容版权**：提取的内容仅用于个人学习，注意版权问题
4. **更新频率**：缓存内容需要定期更新，避免过期

## 参考

- `backend/core/agent/tools/builtin/mediawiki_tool.py` - 类似的知识库工具实现
- `backend/core/agent/tools/builtin/browser_tool.py` - 浏览器工具实现
- `docs/tools/browser-session-management.md` - 浏览器会话管理

