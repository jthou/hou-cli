# MediaWiki 集成服务

MediaWiki 集成服务提供了与 MediaWiki 网站交互的完整功能，包括搜索、读取、编辑页面，以及将 MediaWiki 内容同步到知识库。

## 功能特性

- ✅ **页面搜索**：全文搜索 MediaWiki 页面
- ✅ **页面读取**：获取页面内容和元数据
- ✅ **页面编辑**：编辑现有页面
- ✅ **页面创建**：创建新页面
- ✅ **文件上传**：上传文件到 MediaWiki
- ✅ **知识库同步**：将 MediaWiki 页面同步到本地知识库
- ✅ **统一搜索**：同时在 MediaWiki 和知识库中搜索
- ✅ **AI 助手集成**：AI 助手可以直接访问和操作 MediaWiki

## 快速开始

### 配置

在 `.env` 文件中添加以下配置：

```bash
# MediaWiki 网站 URL
MEDIAWIKI_URL=http://www.jthou.com/mediawiki

# 基本认证（用户名/密码）
MEDIAWIKI_USERNAME=your_username
MEDIAWIKI_PASSWORD=your_password

# Bot 认证（可选，优先使用）
MEDIAWIKI_BOT_NAME=your_bot_name
MEDIAWIKI_BOT_PASSWORD=your_bot_password
```

### 基本使用

#### 客户端服务

```python
from backend.services.mediawiki import MediaWikiClientService

# 创建客户端
client = MediaWikiClientService()
client.connect()

# 搜索页面
results = client.search_pages("关键词", limit=10)

# 获取页面
page = client.get_page("页面标题")

# 编辑页面
client.edit_page("页面标题", "新内容", summary="编辑摘要")

# 创建页面
client.create_page("新页面标题", "页面内容", summary="创建摘要")
```

#### AI 助手工具

AI 助手可以通过 `mediawiki` 工具访问 MediaWiki：

```python
# 在 AI 对话中：
# "搜索 MediaWiki 中关于 Python 的页面"
# AI 会自动调用 mediawiki 工具进行搜索
```

## API 接口

### 搜索 MediaWiki

```
GET /api/mediawiki/search?query=关键词&limit=20
```

**响应示例**：
```json
{
  "success": true,
  "count": 10,
  "results": [
    {
      "title": "页面标题",
      "snippet": "搜索结果摘要",
      "url": "http://www.jthou.com/mediawiki/index.php/页面标题",
      "score": 0.85
    }
  ]
}
```

### 获取页面

```
GET /api/mediawiki/pages/{title}
```

### 编辑页面

```
POST /api/mediawiki/pages/{title}
Content-Type: application/json

{
  "content": "新内容",
  "summary": "编辑摘要"
}
```

### 触发同步

```
POST /api/mediawiki/sync?force=false&category=分类名称
```

### 获取同步状态

```
GET /api/mediawiki/sync/status
```

### 统一搜索

```
GET /api/search/unified?query=关键词&limit=20&sources=mediawiki,knowledge_base
```

## 同步服务

### 全量同步

```python
from backend.services.mediawiki import MediaWikiSyncService

sync_service = MediaWikiSyncService()
result = sync_service.sync_all_pages(force=False)

print(f"同步了 {result['synced']} 个页面")
```

### 增量同步

```python
# 只同步更新的页面
result = sync_service.sync_all_pages(force=False)
```

### 同步指定分类

```python
result = sync_service.sync_category("Category:技术文档")
```

## 统一搜索

```python
from backend.services.mediawiki import UnifiedSearchService

search_service = UnifiedSearchService()

# 同时在 MediaWiki 和知识库中搜索
results = search_service.search("关键词", limit=20)

# 仅搜索 MediaWiki
wiki_results = search_service.search_wiki_only("关键词", limit=10)

# 仅搜索知识库
kb_results = search_service.search_kb_only("关键词", limit=10)
```

## 错误处理

### 连接错误

如果 MediaWiki 连接失败，会抛出 `MediaWikiClientError`：

```python
try:
    client = MediaWikiClientService()
    client.connect()
except MediaWikiClientError as e:
    print(f"连接失败: {e}")
```

### 认证错误

如果认证失败，检查：
1. 用户名和密码是否正确
2. 用户是否有编辑权限
3. Bot 账户是否已创建并配置

## 测试

运行测试：

```bash
# 单元测试
python -m pytest backend/services/mediawiki/tests/

# 特定测试
python -m pytest backend/services/mediawiki/tests/test_client.py
```

**注意**：测试需要配置 MediaWiki 连接信息。

## 架构设计

```
MediaWikiClientService (客户端服务)
    ↓
MediaWikiTool (AI 助手工具)
    ↓
Orchestrator (工具注册)
    ↓
AI Agent (使用工具)
```

## 相关文档

- [MediaWiki API 文档](https://www.mediawiki.org/wiki/API:Main_page)
- [mwclient 文档](https://mwclient.readthedocs.io/)

