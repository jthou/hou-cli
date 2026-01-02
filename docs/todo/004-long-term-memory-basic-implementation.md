# TODO: 长期记忆基础实现

## 任务概述

实现长期记忆模块的基础功能，包括 Memory 数据模型、LongTermMemory 接口、FileLongTermMemory 实现（Memory Store + Index Store，无向量存储），以及 ContextManager 与长期记忆的集成。

**创建时间**: 2025-01-01  
**优先级**: P0（高优先级）  
**预计工时**: 2-3 天  
**状态**: ⏳ 待开始

**前置任务**: 
- [ ] TODO: 上下文存储核心功能实现（004-context-storage-core-implementation）

**关联文档**:
- [主设计文档](../../design/01-context-storage-and-compression-design.md)
- [长期记忆技术选型](../../design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md)

---

## 一、任务范围

### 1.1 核心功能清单

根据设计文档"阶段 2: 长期记忆基础（P0）"，需要实现：

- [ ] **Memory 数据模型**
  - Memory 类（memory_id, memory_type, content, summary, tags, metadata, created_at, updated_at, access_count, last_accessed）
  - MemoryType 枚举（CONVERSATION, KNOWLEDGE, PREFERENCE, CODE, TASK）
  - 序列化/反序列化方法

- [ ] **LongTermMemory 接口**
  - 抽象基类定义
  - 接口方法定义：
    - save_memory
    - get_memory
    - search_memories（关键词搜索，无向量存储）
    - get_memories_by_tags
    - delete_memory
    - update_memory

- [ ] **FileLongTermMemory 实现**
  - Memory Store: JSON 文件存储（`data/long_term_memory/memories/{memory_id}.json`）
  - Index Store: JSON 文件存储（`data/long_term_memory/index.json`）
  - 实现所有 LongTermMemory 接口方法
  - 关键词搜索实现（无向量存储）

- [ ] **ContextManager 与长期记忆集成**
  - 在 ContextManager 中添加 long_term_memory 参数
  - 实现 auto_save_to_memory 功能
  - 实现 get_relevant_memories 方法
  - 在 add_message 中支持保存到长期记忆

- [ ] **长期记忆使用示例（关键词搜索）**
  - 基本使用示例
  - 与 ContextManager 集成示例

---

## 二、实现步骤

### 2.1 阶段 1: Memory 数据模型（0.5天）

#### 步骤 1.1: 实现 MemoryType 枚举
- [ ] 在 `backend/core/context/long_term_memory/models.py` 中定义
- [ ] 枚举值：CONVERSATION, KNOWLEDGE, PREFERENCE, CODE, TASK

#### 步骤 1.2: 实现 Memory 数据模型
- [ ] 实现 `Memory` 数据类
  - memory_id: str
  - memory_type: MemoryType
  - content: str
  - summary: Optional[str]
  - tags: List[str]
  - metadata: Dict[str, Any]
  - created_at: datetime
  - updated_at: datetime
  - access_count: int
  - last_accessed: Optional[datetime]
- [ ] 实现 `to_dict()` 方法
- [ ] 实现 `from_dict()` 类方法

#### 步骤 1.3: 单元测试
- [ ] 创建 `backend/core/context/long_term_memory/tests/test_models.py`
- [ ] 测试 Memory 序列化/反序列化
- [ ] 测试 MemoryType 枚举
- [ ] 测试访问计数和最后访问时间更新

**验收标准**:
- [ ] 所有数据模型测试通过
- [ ] 序列化/反序列化正确

---

### 2.2 阶段 2: LongTermMemory 接口（0.5天）

#### 步骤 2.1: 创建接口定义
- [ ] 创建 `backend/core/context/long_term_memory/base.py`
- [ ] 定义 `LongTermMemory` 抽象基类
- [ ] 定义所有抽象方法：
  - save_memory(memory: Memory) -> bool
  - get_memory(memory_id: str) -> Optional[Memory]
  - search_memories(query: str, memory_type: Optional[MemoryType] = None, top_k: int = 10) -> List[Memory]
  - get_memories_by_tags(tags: List[str], memory_type: Optional[MemoryType] = None) -> List[Memory]
  - delete_memory(memory_id: str) -> bool
  - update_memory(memory: Memory) -> bool

**验收标准**:
- [ ] 接口定义清晰
- [ ] 类型注解完整

---

### 2.3 阶段 3: FileLongTermMemory 实现（1.5天）

#### 步骤 3.1: 实现 Memory Store
- [ ] 创建 `backend/core/context/long_term_memory/file.py`
- [ ] 实现存储目录结构：
  ```
  data/long_term_memory/
  ├── index.json              # 索引文件
  └── memories/
      └── {memory_id}.json    # 记忆文件
  ```
- [ ] 实现 `_get_memory_file()` 方法
- [ ] 实现 `save_memory()` 方法（保存到文件）
- [ ] 实现 `get_memory()` 方法（从文件加载，更新访问信息）

#### 步骤 3.2: 实现 Index Store
- [ ] 实现 `_load_index()` 方法（加载索引文件）
- [ ] 实现 `_save_index()` 方法（保存索引文件）
- [ ] 索引结构：`{"memories": {memory_id: memory_dict}}`
- [ ] 在 save_memory 时更新索引
- [ ] 在 delete_memory 时更新索引

#### 步骤 3.3: 实现搜索功能（关键词搜索）
- [ ] 实现 `search_memories()` 方法：
  - 关键词匹配（content, summary, tags）
  - 支持 memory_type 过滤
  - 支持 top_k 限制
  - 评分机制：content 匹配权重 3，summary 权重 2，tags 权重 1
- [ ] 实现 `get_memories_by_tags()` 方法
- [ ] 实现 `delete_memory()` 方法
- [ ] 实现 `update_memory()` 方法

#### 步骤 3.4: 单元测试
- [ ] 创建 `backend/core/context/long_term_memory/tests/test_file_long_term_memory.py`
- [ ] 测试保存和获取记忆
- [ ] 测试关键词搜索
- [ ] 测试标签搜索
- [ ] 测试删除和更新记忆
- [ ] 测试访问计数更新
- [ ] 测试数据持久化

**验收标准**:
- [ ] 所有 FileLongTermMemory 测试通过
- [ ] 数据持久化正确
- [ ] 搜索功能正确
- [ ] 索引管理正确

---

### 2.4 阶段 4: ContextManager 集成（0.5天）

#### 步骤 4.1: 扩展 ContextManager
- [ ] 在 `ContextManager.__init__()` 中添加参数：
  - long_term_memory: Optional[LongTermMemory] = None
  - auto_save_to_memory: bool = False
- [ ] 修改 `add_message()` 方法：
  - 添加 `save_to_memory: Optional[bool] = None` 参数
  - 如果 auto_save_to_memory 或 save_to_memory 为 True，保存到长期记忆
  - 只保存用户消息（MessageRole.USER）到长期记忆
- [ ] 实现 `get_relevant_memories()` 方法：
  - 从长期记忆搜索相关信息
  - 支持 memory_type 和 top_k 参数

#### 步骤 4.2: 单元测试
- [ ] 在 `test_manager.py` 中添加长期记忆集成测试
- [ ] 测试自动保存到长期记忆
- [ ] 测试手动保存到长期记忆
- [ ] 测试获取相关记忆

**验收标准**:
- [ ] 集成测试通过
- [ ] 自动保存功能正常
- [ ] 记忆检索功能正常

---

### 2.5 阶段 5: 使用示例（0.5天）

#### 步骤 5.1: 创建使用示例
- [ ] 在文档或代码中添加使用示例
- [ ] 基本使用示例（创建长期记忆，保存和搜索）
- [ ] 与 ContextManager 集成示例
- [ ] 自动保存示例

**验收标准**:
- [ ] 使用示例清晰易懂
- [ ] 示例可以正常运行

---

## 三、技术选型

### 3.1 Memory Store

**推荐**: JSON 文件（Python 标准库）

**技术栈**: `json` 标准库

**理由**:
- ✅ 零依赖
- ✅ 可读性强
- ✅ 实现简单

**详细技术选型**: 参考 `docs/design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md` 第 1 节

### 3.2 Index Store

**推荐**: JSON 文件（Python 标准库）

**技术栈**: `json` 标准库

**理由**:
- ✅ 零依赖
- ✅ 与 Memory Store 保持一致
- ✅ 可读性强

**详细技术选型**: 参考 `docs/design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md` 第 3 节

### 3.3 Vector Store

**暂不实现**（阶段 2，P1）

- 当前阶段只实现关键词搜索
- 向量存储和语义搜索在后续阶段实现

---

## 四、模块结构

```
backend/core/context/long_term_memory/
├── __init__.py
├── base.py                 # LongTermMemory 接口
├── models.py               # Memory 数据模型
├── file.py                 # FileLongTermMemory（默认）
└── tests/
    ├── __init__.py
    ├── test_models.py
    └── test_file_long_term_memory.py
```

---

## 五、测试要求

### 5.1 单元测试

- [ ] Memory 数据模型测试
- [ ] FileLongTermMemory 测试
  - 保存和获取记忆
  - 关键词搜索
  - 标签搜索
  - 删除和更新
  - 访问计数

### 5.2 集成测试

- [ ] ContextManager 与长期记忆集成测试
- [ ] 端到端测试：保存 → 搜索 → 检索

### 5.3 测试覆盖率

**目标**: > 80%

---

## 六、验收标准

- [ ] Memory 数据模型实现完成
- [ ] LongTermMemory 接口定义完成
- [ ] FileLongTermMemory 实现完成（Memory Store + Index Store）
- [ ] ContextManager 集成完成
- [ ] 所有单元测试通过
- [ ] 测试覆盖率 > 80%
- [ ] 使用示例可以正常运行
- [ ] 文档完整

---

## 七、注意事项

### 7.1 数据持久化

- ⚠️ 确保索引文件和记忆文件同步更新
- ⚠️ 处理文件不存在的情况
- ⚠️ 处理文件损坏的情况

### 7.2 搜索性能

- ⚠️ 关键词搜索需要遍历所有记忆（中小规模可接受）
- ⚠️ 如果记忆数量很大（> 10万），考虑优化（后续阶段）

### 7.3 内存使用

- ⚠️ Index Store 需要全量加载到内存
- ⚠️ 如果索引很大，考虑分页加载（后续优化）

---

## 八、后续任务

完成本任务后，可以继续：

- [ ] TODO: 长期记忆语义搜索（Vector Store: Chroma）（阶段 5，P1）
- [ ] TODO: 持久化存储扩展（阶段 3，P1）
- [ ] TODO: 高级压缩策略（阶段 4，P1）

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 1.0  
**状态**: ⏳ 待开始

