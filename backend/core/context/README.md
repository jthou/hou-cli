# 上下文存储和整理模块

## 概述

本模块提供了一个**独立、可复用、可扩展**的上下文管理模块，支持多种存储后端、压缩策略和检索方式。该模块可以作为独立组件被不同的 Agent 使用。

## 核心特性

- ✅ **独立性**: 模块化设计，不依赖特定业务逻辑
- ✅ **可复用性**: 可被多个 Agent 或服务使用
- ✅ **可扩展性**: 支持插件化的存储后端和压缩策略
- ✅ **灵活性**: 支持多种使用场景（单会话、多会话、跨设备等）
- ✅ **持久化**: 默认支持持久化存储，数据不丢失
- ✅ **零依赖**: 核心功能使用 Python 标准库，无需额外依赖

## 快速开始

### 基本使用

```python
from backend.core.context import ContextManager, MessageRole

# 创建上下文管理器（使用默认配置）
context_manager = ContextManager()

# 创建会话
session_id = context_manager.create_session()

# 添加消息
context_manager.add_message(session_id, MessageRole.USER, "你好")
context_manager.add_message(session_id, MessageRole.ASSISTANT, "你好！有什么可以帮助你的？")

# 获取消息
messages = context_manager.get_messages(session_id)
for msg in messages:
    print(f"{msg.role.value}: {msg.content}")

# 获取用于 LLM 的格式
llm_messages = context_manager.get_messages_for_llm(session_id)
```

### 使用文件存储（持久化）

```python
from pathlib import Path
from backend.core.context import ContextManager

# 指定存储目录
context_manager = ContextManager(storage_dir=Path("data/contexts"))

# 使用方式与基本使用相同
session_id = context_manager.create_session()
context_manager.add_message(session_id, MessageRole.USER, "消息内容")
```

### 消息压缩

#### 时间窗口压缩（默认）

```python
# 设置默认最大消息数
context_manager = ContextManager(default_max_messages=10)

# 添加多条消息
for i in range(20):
    context_manager.add_message(session_id, MessageRole.USER, f"消息{i}")

# 获取消息（自动压缩到 10 条）
messages = context_manager.get_messages(session_id)
# 将只返回最近 10 条消息
```

#### Token 限制压缩

```python
from backend.core.context.compression.token_limit import TokenLimitCompression

# 使用 TokenLimitCompression
compression = TokenLimitCompression()
context_manager = ContextManager(
    compression_strategy=compression,
    default_max_tokens=1000
)

# 添加多条长消息
for i in range(20):
    context_manager.add_message(session_id, MessageRole.USER, f"消息{i}: " + "x" * 100)

# 获取消息（自动压缩到 1000 tokens 以内）
messages = context_manager.get_messages(session_id)
# 优先保留系统消息，然后从后往前保留其他消息
```

#### 重要性评分压缩

```python
from backend.core.context.compression.importance import ImportanceScoringCompression

# 使用 ImportanceScoringCompression
compression = ImportanceScoringCompression()
context_manager = ContextManager(
    compression_strategy=compression,
    default_max_messages=10
)

# 添加消息（包含重要消息）
context_manager.add_message(session_id, MessageRole.SYSTEM, "系统配置")
context_manager.add_message(session_id, MessageRole.USER, "普通消息")
context_manager.add_message(session_id, MessageRole.USER, "重要的问题需要解决")

# 获取消息（按重要性压缩）
messages = context_manager.get_messages(session_id)
# 会优先保留系统消息和包含关键词的重要消息
```

### 搜索消息

```python
# 添加消息
context_manager.add_message(session_id, MessageRole.USER, "Python 编程")
context_manager.add_message(session_id, MessageRole.USER, "Java 开发")

# 搜索相关消息
results = context_manager.search_messages(session_id, "Python", top_k=5)
for msg in results:
    print(f"{msg.role.value}: {msg.content}")
```

## 模块结构

```
backend/core/context/
├── __init__.py                 # 导出主要接口
├── models.py                   # Message, Session 数据模型
├── manager.py                 # ContextManager 主类
├── examples.py                # 使用示例
├── storage/
│   ├── base.py                # StorageBackend 接口
│   └── file.py                # FileStorageBackend（默认，持久化）
├── compression/
│   ├── base.py                # CompressionStrategy 接口
│   ├── time_window.py         # TimeWindowCompression（默认）
│   ├── token_limit.py        # TokenLimitCompression
│   └── importance.py          # ImportanceScoringCompression
└── retrieval/
    ├── base.py                # RetrievalEngine 接口
    └── keyword.py             # KeywordRetrievalEngine（基础）
```

## API 文档

### ContextManager

#### `__init__()`

初始化上下文管理器。

**参数**:
- `storage_backend` (Optional[StorageBackend]): 存储后端，默认使用 FileStorageBackend
- `compression_strategy` (Optional[CompressionStrategy]): 压缩策略，默认使用 TimeWindowCompression
- `retrieval_engine` (Optional[RetrievalEngine]): 检索引擎，默认使用 KeywordRetrievalEngine
- `storage_dir` (Optional[Path]): 存储目录（仅当使用默认 FileStorageBackend 时有效）
- `default_max_messages` (int): 默认最大消息数，默认 10
- `default_max_tokens` (Optional[int]): 默认最大 token 数，默认 None

#### `create_session(metadata=None) -> str`

创建新会话。

**参数**:
- `metadata` (Optional[Dict[str, Any]]): 会话元数据

**返回**: 会话 ID

#### `add_message(session_id, role, content, metadata=None) -> str`

添加消息。

**参数**:
- `session_id` (str): 会话 ID
- `role` (MessageRole): 消息角色
- `content` (str): 消息内容
- `metadata` (Optional[Dict[str, Any]]): 消息元数据

**返回**: 消息 ID

#### `get_messages(session_id, max_messages=None, max_tokens=None, compressed=True) -> List[Message]`

获取消息列表。

**参数**:
- `session_id` (str): 会话 ID
- `max_messages` (Optional[int]): 最大消息数（None 使用默认值）
- `max_tokens` (Optional[int]): 最大 token 数（None 使用默认值）
- `compressed` (bool): 是否应用压缩，默认 True

**返回**: 消息列表

#### `get_messages_for_llm(session_id, max_messages=None, max_tokens=None) -> List[Dict[str, str]]`

获取用于 LLM 的消息格式。

**参数**:
- `session_id` (str): 会话 ID
- `max_messages` (Optional[int]): 最大消息数
- `max_tokens` (Optional[int]): 最大 token 数

**返回**: LLM 格式的消息列表

#### `search_messages(session_id, query, top_k=5) -> List[Message]`

搜索相关消息。

**参数**:
- `session_id` (str): 会话 ID
- `query` (str): 搜索查询
- `top_k` (int): 返回前 K 条消息，默认 5

**返回**: 相关消息列表

#### `clear_session(session_id) -> bool`

清除会话。

**参数**:
- `session_id` (str): 会话 ID

**返回**: 是否成功

#### `get_session(session_id) -> Optional[Session]`

获取会话。

**参数**:
- `session_id` (str): 会话 ID

**返回**: 会话对象或 None

#### `list_sessions(limit=None) -> List[Session]`

列出会话。

**参数**:
- `limit` (Optional[int]): 限制返回数量

**返回**: 会话列表（按更新时间倒序）

## 数据模型

### Message

消息数据模型。

**字段**:
- `role` (MessageRole): 消息角色
- `content` (str): 消息内容
- `timestamp` (datetime): 时间戳
- `metadata` (Dict[str, Any]): 元数据
- `message_id` (Optional[str]): 消息 ID

### Session

会话数据模型。

**字段**:
- `session_id` (str): 会话 ID
- `created_at` (datetime): 创建时间
- `updated_at` (datetime): 更新时间
- `metadata` (Dict[str, Any]): 元数据

### MessageRole

消息角色枚举。

**值**:
- `SYSTEM`: 系统消息
- `USER`: 用户消息
- `ASSISTANT`: 助手消息
- `TOOL`: 工具消息

## 存储后端

### FileStorageBackend（默认）

使用 JSON 文件存储，支持持久化。

**存储结构**:
```
data/contexts/
├── sessions.json          # 会话列表
└── {session_id}/
    └── messages.json       # 会话消息
```

## 压缩策略

### TimeWindowCompression（默认）

时间窗口压缩策略，保留最近的消息。

**特点**:
- 支持 `max_messages` 参数
- 保留最近的消息
- 如果消息数 <= max_messages，返回全部消息
- **性能**: 最快（O(1) 复杂度）

### TokenLimitCompression

Token 限制压缩策略，基于 token 数量压缩消息。

**特点**:
- 支持 `max_tokens` 和 `max_messages` 参数
- 优先保留系统消息
- 从后往前保留其他消息
- 支持自定义 tokenizer（默认：1 token ≈ 4 字符）
- **性能**: 较快（O(n) 复杂度）

**使用场景**: 需要精确控制 token 数量的场景

### ImportanceScoringCompression

重要性评分压缩策略，基于消息重要性压缩。

**特点**:
- 支持 `max_tokens` 和 `max_messages` 参数
- 重要性评分规则：
  - 系统消息：+10.0
  - 最近 5 条消息：+5.0
  - 包含关键词（"错误", "问题", "重要", "关键", "失败", "异常"）：+2.0
  - 用户消息：+1.0
- 按分数排序选择消息
- 按时间顺序重新排序
- **性能**: 较慢（O(n²) 复杂度），但保留重要消息效果最好

**使用场景**: 需要保留重要消息的场景

## 检索引擎

### KeywordRetrievalEngine（默认）

关键词检索引擎（基础版本），支持简单关键词匹配。

**特点**:
- 支持关键词搜索
- 按匹配分数排序
- 返回 top_k 条消息

## 测试

运行测试：

```bash
# 运行所有测试
pytest backend/core/context/ -v

# 运行特定测试
pytest backend/core/context/tests/test_models.py -v
pytest backend/core/context/tests/test_manager.py -v
```

## 示例代码

查看 `examples.py` 文件获取更多使用示例。

运行示例：

```bash
python backend/core/context/examples.py
```

## 相关文档

- [设计文档](../../../docs/design/01-context-storage-and-compression-design.md)
- [技术选型文档](../../../docs/design/01-context-storage-and-compression-design-technology-selection.md)
- [TDD 指南](../../../docs/todo/004-context-storage-core-implementation-tdd-guide.md)

## 性能基准

详细的性能基准数据请参考：[性能基准文档](../../../docs/design/01-context-storage-compression-performance-benchmark.md)

**性能对比**（10000 条消息）:
- TimeWindowCompression: < 0.0001s
- TokenLimitCompression: 0.0072s
- ImportanceScoringCompression: 0.0352s

## 未来扩展

- [x] ✅ 长期记忆支持
- [x] ✅ 高级压缩策略（TokenLimitCompression, ImportanceScoringCompression）
- [x] ✅ 数据库存储后端（SQLite）
- [ ] 语义搜索（向量检索）
- [ ] 更完善的检索引擎

