# 知乎直达工具使用指南

## 概述

知乎直达工具（`zhihu_zhida`）允许你访问和提取知乎直达（https://zhida.zhihu.com）的问题和答案内容。知乎直达是一个提问式的网页知识库，每个 URL 对应一个特定的问题和多个答案。

## 功能特性

- ✅ **读取内容**：访问知乎直达页面并提取问题和答案
- ✅ **结构化提取**：提取结构化的 JSON 数据
- ✅ **本地缓存**：自动缓存内容，提高访问速度
- ✅ **知识库保存**：可选保存到本地知识库
- ✅ **多格式输出**：支持 Markdown、JSON、Text 格式
- ✅ **登录支持**：自动使用已保存的知乎登录状态

## 基本使用

### 示例1：读取问题和答案

```
用户：读取知乎直达 https://zhida.zhihu.com/search/3707579171380201696 的内容

AI 会自动调用：
zhihu_zhida(
    url="3707579171380201696",
    operation="read",
    format="markdown"
)
```

**输出**：格式化的 Markdown 内容，包括问题标题、描述和所有答案。

### 示例2：使用搜索 ID

```
用户：读取知乎直达 3707579171380201696

AI 会自动识别并调用工具
```

**说明**：可以直接使用搜索 ID，无需完整 URL。

### 示例3：提取结构化数据

```
用户：提取知乎直达 https://zhida.zhihu.com/search/3707579171380201696 的结构化数据

AI 调用：
zhihu_zhida(
    url="3707579171380201696",
    operation="extract",
    format="json"
)
```

**输出**：JSON 格式的结构化数据，包含问题、答案、元数据等。

### 示例4：保存到知识库

```
用户：将知乎直达 https://zhida.zhihu.com/search/3707579171380201696 保存到知识库

AI 调用：
zhihu_zhida(
    url="3707579171380201696",
    operation="read",
    save_to_kb=true
)
```

**说明**：内容会保存到 `{app_data_dir}/knowledge/zhihu_zhida/` 目录。

## 工具参数

### `url`（必需）

- **类型**：string
- **说明**：知乎直达 URL 或搜索 ID
- **示例**：
  - `"3707579171380201696"`
  - `"https://zhida.zhihu.com/search/3707579171380201696"`

### `operation`（可选）

- **类型**：string
- **默认值**：`"read"`
- **选项**：
  - `"read"`：读取并返回格式化内容
  - `"extract"`：提取结构化 JSON 数据
  - `"save"`：保存到知识库

### `format`（可选）

- **类型**：string
- **默认值**：`"markdown"`
- **选项**：
  - `"markdown"`：Markdown 格式（适合阅读）
  - `"json"`：JSON 格式（适合程序处理）
  - `"text"`：纯文本格式

### `save_to_kb`（可选）

- **类型**：boolean
- **默认值**：`false`
- **说明**：是否保存到知识库（仅在 `operation="read"` 时有效）

## 数据存储位置

### 缓存目录

- **位置**：`{app_data_dir}/cache/zhihu_zhida/`
- **格式**：`{search_id}.json`
- **用途**：临时缓存，提高访问速度

### 知识库目录

- **位置**：`{app_data_dir}/knowledge/zhihu_zhida/`
- **格式**：`{search_id}.json`
- **用途**：长期存储，支持离线访问

### 配置目录位置

- **macOS**: `~/Library/Application Support/hou-cli/`
- **Linux**: `~/.local/share/hou-cli/`
- **Windows**: `%LOCALAPPDATA%\hou-cli\`

## 使用场景

### 场景1：快速查询

```
用户：知乎直达 3707579171380201696 讲的是什么？

AI：使用 zhihu_zhida 工具读取内容并回答
```

### 场景2：批量保存

```
用户：将这些知乎直达保存到知识库：
1. 3707579171380201696
2. 1234567890123456789
3. 9876543210987654321

AI：逐个调用 zhihu_zhida 工具并保存
```

### 场景3：结构化分析

```
用户：提取知乎直达 3707579171380201696 的所有答案，分析答案质量

AI：使用 extract 操作获取结构化数据，然后进行分析
```

## 输出格式示例

### Markdown 格式

```markdown
# 问题标题

**链接**: [https://zhida.zhihu.com/search/3707579171380201696](...)

## 问题描述

问题的详细描述内容...

## 答案

### 答案 1
**作者**: 用户名
**点赞数**: 123
**时间**: 2024-01-01

答案内容...

### 答案 2
...
```

### JSON 格式

```json
{
  "search_id": "3707579171380201696",
  "url": "https://zhida.zhihu.com/search/3707579171380201696",
  "question_title": "问题标题",
  "question_content": "问题描述",
  "answers": [
    {
      "author": "用户名",
      "content": "答案内容",
      "upvotes": 123,
      "time": "2024-01-01"
    }
  ],
  "metadata": {}
}
```

## 注意事项

### 1. 登录状态

- 工具会自动使用已保存的知乎登录状态（`user_data_dir="zhihu"`）
- 如果未登录，部分内容可能无法访问
- 首次使用建议先登录知乎（使用 browser 工具）

### 2. 缓存机制

- 内容会自动缓存到本地
- 缓存不会自动过期，需要手动删除或重新获取
- 使用 `operation="extract"` 会强制获取最新内容

### 3. 网络要求

- 需要网络连接访问知乎
- 首次访问需要加载页面，可能需要较长时间
- 建议在网络良好时使用

### 4. 内容版权

- 提取的内容仅用于个人学习
- 注意遵守知乎的使用条款
- 不要大规模批量抓取

## 故障排查

### 问题1：无法访问内容

**症状**：工具返回错误，提示无法获取内容

**解决方案**：
1. 检查网络连接
2. 确认 URL 或搜索 ID 正确
3. 确保浏览器工具已登录知乎
4. 尝试使用 browser 工具手动访问

### 问题2：内容提取不完整

**症状**：提取的内容缺少部分答案

**解决方案**：
1. 知乎页面可能需要滚动加载更多内容
2. 尝试增加 browser 工具的 timeout
3. 使用 `operation="extract"` 获取最新内容

### 问题3：登录状态丢失

**症状**：提示需要登录

**解决方案**：
1. 使用 browser 工具重新登录知乎
2. 确保使用 `user_data_dir="zhihu"` 保存登录状态
3. 检查浏览器会话是否过期

## 与浏览器工具的关系

知乎直达工具内部使用 browser 工具来访问网页和提取内容：

1. **依赖关系**：需要 browser 工具可用
2. **会话复用**：自动使用知乎登录状态
3. **内容提取**：使用 browser-use 的 extract action

## 未来改进

- [ ] 支持批量操作（一次读取多个 URL）
- [ ] 支持搜索相关问题
- [ ] 集成向量数据库，支持语义搜索
- [ ] 支持定期同步更新
- [ ] 支持导出为其他格式（PDF、Word 等）

## 参考

- `docs/design/zhihu-zhida-integration.md` - 详细设计文档
- `docs/tools/browser-session-management.md` - 浏览器会话管理
- `backend/core/agent/tools/builtin/zhihu_zhida_tool.py` - 工具实现

