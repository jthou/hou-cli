# TODO: 上下文存储核心功能实现

## 任务概述

实现上下文存储和整理机制的核心功能，包括数据模型、存储后端接口、压缩策略接口和 ContextManager 统一接口。

**创建时间**: 2025-01-01  
**优先级**: P0（高优先级）  
**预计工时**: 3-5 天  
**状态**: ✅ 已完成  
**完成时间**: 2025-01-02  
**审查报告**: [004-context-storage-completion-review.md](./004-context-storage-completion-review.md)

**关联文档**:
- [主设计文档](../../design/01-context-storage-and-compression-design.md)
- [技术选型文档](../../design/01-context-storage-and-compression-design-technology-selection.md)
- [TDD 指南](./004-context-storage-core-implementation-tdd-guide.md) ⭐

---

## 一、任务范围

### 1.1 核心功能清单

根据设计文档"阶段 1: 核心功能（P0）"，需要实现：

- [x] **Message 和 Session 数据模型** ✅
  - Message 类（role, content, timestamp, metadata, message_id）
  - Session 类（session_id, created_at, updated_at, metadata）
  - 序列化/反序列化方法（to_dict, from_dict）
  - **测试**: 9个测试通过，覆盖率 100%

- [x] **StorageBackend 接口** ✅
  - 抽象基类定义
  - 接口方法定义（save_message, get_messages, delete_message, clear_session, create_session, get_session, list_sessions）
  - **测试**: 接口定义完整

- [x] **FileStorageBackend 实现（持久化，默认）** ✅ ⭐
  - 使用 JSON 文件存储（Python 标准库）
  - 会话目录结构：`data/contexts/{session_id}/messages.json`
  - 会话列表：`data/contexts/sessions.json`
  - 实现所有 StorageBackend 接口方法
  - **测试**: 8个测试通过，覆盖率 97%

- [x] **CompressionStrategy 接口** ✅
  - 抽象基类定义
  - compress 方法接口
  - **测试**: 接口定义完整

- [x] **TimeWindowCompression 实现** ✅
  - 时间窗口压缩策略（保留最近的消息）
  - 支持 max_messages 参数
  - **测试**: 4个测试通过，覆盖率 100%

- [x] **ContextManager 统一接口** ✅
  - 初始化方法（支持自定义 storage_backend, compression_strategy, retrieval_engine）
  - create_session: 创建新会话
  - add_message: 添加消息
  - get_messages: 获取消息列表（支持压缩）
  - get_messages_for_llm: 获取用于 LLM 的消息格式
  - search_messages: 搜索相关消息（基础关键词搜索）
  - clear_session: 清除会话
  - get_session: 获取会话
  - list_sessions: 列出会话
  - **测试**: 10个测试通过，覆盖率 98%

- [x] **基本使用示例** ✅
  - 基本使用示例代码
  - 使用文件存储示例
  - 使用 Token 限制压缩示例
  - **文件**: examples.py 已创建

- [x] **基础 KeywordRetrievalEngine（最基础版本）** ✅
  - RetrievalEngine 接口定义
  - KeywordRetrievalEngine 基础实现（仅简单关键词匹配）
  - **注意**: 详细完善将在阶段 5 实现
  - **测试**: 测试通过，覆盖率 100%

---

## 二、实现步骤

### 2.1 阶段 1: 数据模型（1天）

#### 步骤 1.1: 创建模块结构
- [ ] 创建 `backend/core/context/` 目录
- [ ] 创建 `__init__.py` 导出主要接口
- [ ] 创建 `models.py` 文件

#### 步骤 1.2: 实现 Message 数据模型
- [ ] 定义 `MessageRole` 枚举（SYSTEM, USER, ASSISTANT, TOOL）
- [ ] 实现 `Message` 数据类
  - role: MessageRole
  - content: str
  - timestamp: datetime
  - metadata: Dict[str, Any]
  - message_id: Optional[str]
- [ ] 实现 `to_dict()` 方法
- [ ] 实现 `from_dict()` 类方法

#### 步骤 1.3: 实现 Session 数据模型
- [ ] 实现 `Session` 数据类
  - session_id: str
  - created_at: datetime
  - updated_at: datetime
  - metadata: Dict[str, Any]
- [ ] 实现 `to_dict()` 方法
- [ ] 实现 `from_dict()` 类方法

#### 步骤 1.4: 单元测试（TDD 方式）
- [ ] 创建 `backend/core/context/tests/test_models.py`
- [ ] **先写测试**（TDD Red 阶段）:
  - 测试 Message 创建
  - 测试 Message 序列化/反序列化
  - 测试 Session 创建
  - 测试 Session 序列化/反序列化
  - 测试 MessageRole 枚举
- [ ] **运行测试，确认失败**（验证测试有效）
- [ ] **实现功能**（TDD Green 阶段）
- [ ] **运行测试，确认通过**

**TDD 验证**:
- [ ] 测试必须先失败（功能未实现时）
- [ ] 实现功能后测试必须通过
- [ ] 如果测试一开始就通过，说明测试无效

**详细 TDD 指南**: 参考 `docs/todo/004-context-storage-core-implementation-tdd-guide.md`

**验收标准**:
- [ ] 所有数据模型测试通过
- [ ] 序列化/反序列化正确
- [ ] 类型检查通过（mypy）
- [ ] TDD 流程验证通过

---

### 2.2 阶段 2: 存储后端接口和实现（1.5天）

#### 步骤 2.1: 创建存储后端接口
- [ ] 创建 `backend/core/context/storage/` 目录
- [ ] 创建 `base.py` 定义 `StorageBackend` 抽象基类
- [ ] 定义所有抽象方法：
  - save_message
  - get_messages
  - delete_message
  - clear_session
  - create_session
  - get_session
  - list_sessions

#### 步骤 2.2: 实现 FileStorageBackend
- [ ] 创建 `file.py` 实现 `FileStorageBackend`
- [ ] 实现存储目录结构：
  ```
  data/contexts/
  ├── sessions.json          # 会话列表
  └── {session_id}/
      └── messages.json       # 会话消息
  ```
- [ ] 实现 `_load_sessions()` 和 `_save_sessions()` 方法
- [ ] 实现 `save_message()` 方法
- [ ] 实现 `get_messages()` 方法（支持 limit 和 offset）
- [ ] 实现 `delete_message()` 方法
- [ ] 实现 `clear_session()` 方法
- [ ] 实现 `create_session()` 方法
- [ ] 实现 `get_session()` 方法
- [ ] 实现 `list_sessions()` 方法

#### 步骤 2.3: 单元测试（TDD 方式）
- [ ] 创建 `backend/core/context/storage/tests/test_file_storage.py`
- [ ] **先写测试**（TDD Red 阶段）:
  - 测试保存和获取消息
  - 测试删除消息
  - 测试会话管理
  - 测试 limit 和 offset
  - 测试数据持久化（重启后数据不丢失）
- [ ] **运行测试，确认失败**（验证测试有效）
- [ ] **实现功能**（TDD Green 阶段）
- [ ] **运行测试，确认通过**

**TDD 验证**: 参考阶段 1 的 TDD 验证方法

**验收标准**:
- [ ] 所有存储后端测试通过
- [ ] 数据持久化正确
- [ ] 文件结构符合设计
- [ ] 错误处理完善

---

### 2.3 阶段 3: 压缩策略接口和实现（0.5天）

#### 步骤 3.1: 创建压缩策略接口
- [ ] 创建 `backend/core/context/compression/` 目录
- [ ] 创建 `base.py` 定义 `CompressionStrategy` 抽象基类
- [ ] 定义 `compress()` 抽象方法

#### 步骤 3.2: 实现 TimeWindowCompression
- [ ] 创建 `time_window.py` 实现 `TimeWindowCompression`
- [ ] 实现 `compress()` 方法：
  - 支持 max_messages 参数
  - 保留最近的消息
  - 如果消息数 <= max_messages，返回全部消息

#### 步骤 3.3: 单元测试（TDD 方式）
- [ ] 创建 `backend/core/context/compression/tests/test_time_window.py`
- [ ] **先写测试**（TDD Red 阶段）:
  - 测试消息数未超过限制
  - 测试消息数超过限制（保留最近的消息）
  - 测试空消息列表
- [ ] **运行测试，确认失败**（验证测试有效）
- [ ] **实现功能**（TDD Green 阶段）
- [ ] **运行测试，确认通过**

**TDD 验证**: 参考阶段 1 的 TDD 验证方法

**验收标准**:
- [ ] 所有压缩策略测试通过
- [ ] 压缩逻辑正确
- [ ] 边界情况处理正确

---

### 2.4 阶段 4: ContextManager 统一接口（1天）

#### 步骤 4.1: 实现 ContextManager
- [ ] 创建 `manager.py` 实现 `ContextManager` 类
- [ ] 实现 `__init__()` 方法：
  - 默认使用 `FileStorageBackend`
  - 默认使用 `TimeWindowCompression`
  - 默认使用 `KeywordRetrievalEngine`（基础实现）
  - 支持自定义参数
- [ ] 实现 `create_session()` 方法
- [ ] 实现 `add_message()` 方法
- [ ] 实现 `get_messages()` 方法（支持压缩）
- [ ] 实现 `get_messages_for_llm()` 方法
- [ ] 实现 `search_messages()` 方法（基础关键词搜索）
- [ ] 实现 `clear_session()` 方法
- [ ] 实现 `get_session()` 方法
- [ ] 实现 `list_sessions()` 方法

#### 步骤 4.2: 实现基础 KeywordRetrievalEngine（最基础版本）
- [ ] 创建 `backend/core/context/retrieval/` 目录
- [ ] 创建 `base.py` 定义 `RetrievalEngine` 接口
- [ ] 创建 `keyword.py` 实现**最基础**关键词搜索
  - **注意**: 这是最基础版本，仅支持简单关键词匹配
  - 详细完善（部分匹配、模糊匹配等）将在阶段 5（任务 004-retrieval-and-semantic-search）中实现

#### 步骤 4.3: 单元测试（TDD 方式）
- [ ] 创建 `backend/core/context/tests/test_manager.py`
- [ ] **先写测试**（TDD Red 阶段）:
  - 测试创建会话
  - 测试添加和获取消息
  - 测试消息压缩
  - 测试搜索消息
  - 测试会话管理
- [ ] **运行测试，确认失败**（验证测试有效）
- [ ] **实现功能**（TDD Green 阶段）
- [ ] **运行测试，确认通过**

**TDD 验证**: 参考阶段 1 的 TDD 验证方法

**验收标准**:
- [ ] 所有 ContextManager 测试通过
- [ ] 接口使用简单直观
- [ ] 默认配置合理

---

### 2.5 阶段 5: 使用示例和文档（0.5天）

#### 步骤 5.1: 创建使用示例
- [ ] 在 `manager.py` 或单独文件中添加使用示例
- [ ] 基本使用示例
- [ ] 使用文件存储示例
- [ ] 使用压缩策略示例

#### 步骤 5.2: 更新文档
- [ ] 更新 `README.md` 或创建使用文档
- [ ] 添加快速开始指南
- [ ] 添加 API 文档

**验收标准**:
- [ ] 使用示例清晰易懂
- [ ] 文档完整

---

## 三、技术选型

### 3.1 存储后端

**推荐**: FileStorageBackend（JSON 文件）

**技术栈**: Python 标准库 `json`

**理由**:
- ✅ 零依赖（标准库）
- ✅ 可读性强（人类可读）
- ✅ 持久化存储
- ✅ 实现简单

**详细技术选型**: 参考 `docs/design/01-context-storage-and-compression-design-technology-selection.md`

### 3.2 压缩策略

**推荐**: TimeWindowCompression（时间窗口压缩）

**理由**:
- ✅ 实现简单
- ✅ 满足基本需求
- ✅ 性能好

---

## 四、模块结构

```
backend/core/context/
├── __init__.py                 # 导出主要接口
├── manager.py                  # ContextManager 主类
├── models.py                   # Message, Session 数据模型
├── storage/
│   ├── __init__.py
│   ├── base.py                 # StorageBackend 接口
│   └── file.py                 # FileStorageBackend（默认，持久化）
├── compression/
│   ├── __init__.py
│   ├── base.py                 # CompressionStrategy 接口
│   └── time_window.py          # TimeWindowCompression
└── retrieval/
    ├── __init__.py
    ├── base.py                 # RetrievalEngine 接口
    └── keyword.py              # KeywordRetrievalEngine（基础）
```

---

## 五、测试要求

### 5.1 单元测试

- [ ] Message 和 Session 数据模型测试
- [ ] FileStorageBackend 测试
- [ ] TimeWindowCompression 测试
- [ ] ContextManager 测试
- [ ] KeywordRetrievalEngine 测试

### 5.2 集成测试

- [ ] 端到端测试：创建会话 → 添加消息 → 获取消息 → 压缩
- [ ] 持久化测试：重启后数据不丢失
- [ ] 搜索功能测试（基础关键词搜索）
- [ ] ContextManager 与 FileStorageBackend 集成测试
- [ ] ContextManager 与 TimeWindowCompression 集成测试

### 5.3 测试覆盖率

**目标**: > 80%

---

## 六、验收标准

- [ ] 所有核心功能实现完成
- [ ] 所有单元测试通过
- [ ] 测试覆盖率 > 80%
- [ ] 代码质量检查通过（lint, type check）
- [ ] 使用示例可以正常运行
- [ ] 文档完整

---

## 七、注意事项

### 7.1 数据持久化

- ⚠️ 确保文件写入是原子的（避免数据损坏）
- ⚠️ 处理文件不存在的情况
- ⚠️ 处理文件损坏的情况

### 7.2 性能考虑

- ⚠️ 大量消息时，JSON 序列化/反序列化可能较慢
- ⚠️ 考虑添加缓存机制（如需要）

### 7.3 错误处理

- ⚠️ 文件读写错误处理
- ⚠️ JSON 解析错误处理
- ⚠️ 数据验证错误处理

---

## 八、后续任务

完成本任务后，可以继续：

- [ ] TODO: 长期记忆基础实现（阶段 2，P0）
- [ ] TODO: 持久化存储扩展（阶段 3，P1）
- [ ] TODO: 高级压缩策略（阶段 4，P1）
- [ ] TODO: 检索功能和语义搜索（阶段 5，P1）

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 1.0  
**状态**: ⏳ 待开始

