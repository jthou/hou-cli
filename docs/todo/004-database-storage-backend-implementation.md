# TODO: 数据库存储后端实现

## 任务概述

实现 DatabaseStorageBackend（SQLite），提供数据库存储能力，支持 SQL 查询和事务。

**创建时间**: 2025-01-01  
**优先级**: P1（中优先级）  
**预计工时**: 1-2 天  
**状态**: ⏳ 待开始

**前置任务**: 
- [ ] TODO: 上下文存储核心功能实现（004-context-storage-core-implementation）

**关联文档**:
- [主设计文档](../../design/01-context-storage-and-compression-design.md)
- [技术选型文档](../../design/01-context-storage-and-compression-design-technology-selection.md)

---

## 一、任务范围

### 1.1 核心功能清单

根据设计文档"阶段 3: 持久化存储（P1）"，需要实现：

- [ ] **DatabaseStorageBackend 实现**
  - 使用 SQLite（Python 标准库 `sqlite3`）
  - 数据库表结构设计（sessions 表、messages 表）
  - 索引创建（session_id, timestamp）
  - 实现所有 StorageBackend 接口方法

- [ ] **存储后端切换测试**
  - 测试从 FileStorageBackend 切换到 DatabaseStorageBackend
  - 测试数据迁移（可选）
  - 测试不同存储后端的兼容性

---

## 二、实现步骤

### 2.1 阶段 1: 数据库表结构设计（0.5天）

#### 步骤 1.1: 设计表结构
- [ ] 设计 sessions 表：
  - session_id (TEXT PRIMARY KEY)
  - created_at (TEXT NOT NULL)
  - updated_at (TEXT NOT NULL)
  - metadata (TEXT) - JSON 字符串
- [ ] 设计 messages 表：
  - message_id (TEXT PRIMARY KEY)
  - session_id (TEXT NOT NULL, FOREIGN KEY)
  - role (TEXT NOT NULL)
  - content (TEXT NOT NULL)
  - timestamp (TEXT NOT NULL)
  - metadata (TEXT) - JSON 字符串
- [ ] 设计索引：
  - idx_messages_session_id (session_id)
  - idx_messages_timestamp (timestamp)

#### 步骤 1.2: 实现数据库初始化
- [ ] 创建 `backend/core/context/storage/database.py`
- [ ] 实现 `_init_db()` 方法：
  - 创建 sessions 表
  - 创建 messages 表
  - 创建外键约束
  - 创建索引

**验收标准**:
- [ ] 表结构符合设计
- [ ] 索引创建正确
- [ ] 外键约束正确

---

### 2.2 阶段 2: 实现 StorageBackend 接口（1天）

#### 步骤 2.1: 实现基础方法
- [ ] 实现 `_get_conn()` 方法（获取数据库连接）
- [ ] 实现 `save_message()` 方法：
  - 插入或更新消息
  - 更新会话的 updated_at
  - 使用事务确保一致性
- [ ] 实现 `get_messages()` 方法：
  - 支持 limit 和 offset
  - 按 timestamp 排序
  - 返回 Message 对象列表

#### 步骤 2.2: 实现会话管理方法
- [ ] 实现 `create_session()` 方法
- [ ] 实现 `get_session()` 方法
- [ ] 实现 `list_sessions()` 方法（按 updated_at 排序）
- [ ] 实现 `delete_message()` 方法
- [ ] 实现 `clear_session()` 方法（删除会话及其所有消息）

#### 步骤 2.3: 错误处理和事务
- [ ] 实现事务处理（commit, rollback）
- [ ] 实现错误处理（数据库错误、连接错误）
- [ ] 实现连接关闭（确保资源释放）

#### 步骤 2.4: 单元测试
- [ ] 创建 `backend/core/context/storage/tests/test_database_storage.py`
- [ ] 测试保存和获取消息
- [ ] 测试删除消息
- [ ] 测试会话管理
- [ ] 测试 limit 和 offset
- [ ] 测试事务回滚
- [ ] 测试并发访问（如需要）

**验收标准**:
- [ ] 所有 StorageBackend 接口方法实现完成
- [ ] 所有单元测试通过
- [ ] 事务处理正确
- [ ] 错误处理完善

---

### 2.3 阶段 3: 存储后端切换测试（0.5天）

#### 步骤 3.1: 兼容性测试
- [ ] 测试 FileStorageBackend 和 DatabaseStorageBackend 的接口兼容性
- [ ] 测试 ContextManager 可以无缝切换存储后端
- [ ] 测试不同存储后端的数据一致性

#### 步骤 3.2: 性能对比测试（可选）
- [ ] 对比 FileStorageBackend 和 DatabaseStorageBackend 的性能
- [ ] 测试不同数据量下的性能表现

**验收标准**:
- [ ] 存储后端可以无缝切换
- [ ] 数据一致性正确
- [ ] 性能测试结果记录

---

## 三、技术选型

### 3.1 数据库

**推荐**: SQLite（Python 标准库）

**技术栈**: `sqlite3` 标准库

**理由**:
- ✅ 零依赖（标准库）
- ✅ 轻量级（单文件数据库）
- ✅ 支持 SQL 查询和事务
- ✅ 性能好（适合中小规模）

**详细技术选型**: 参考 `docs/design/01-context-storage-and-compression-design-technology-selection.md` 第 3 节

---

## 四、数据库设计

### 4.1 Sessions 表

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT
);
```

### 4.2 Messages 表

```sql
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

### 4.3 索引

```sql
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
```

---

## 五、测试要求

### 5.1 单元测试

- [ ] DatabaseStorageBackend 所有方法测试
- [ ] 事务测试
- [ ] 错误处理测试
- [ ] 并发测试（如需要）

### 5.2 集成测试

- [ ] 存储后端切换测试
- [ ] ContextManager 集成测试

### 5.3 测试覆盖率

**目标**: > 80%

---

## 六、验收标准

- [ ] DatabaseStorageBackend 实现完成
- [ ] 所有 StorageBackend 接口方法实现
- [ ] 数据库表结构和索引正确
- [ ] 所有单元测试通过
- [ ] 测试覆盖率 > 80%
- [ ] 存储后端可以无缝切换
- [ ] 文档完整

---

## 七、注意事项

### 7.1 数据库连接管理

- ⚠️ 确保连接正确关闭（使用 try-finally）
- ⚠️ 处理连接池（如需要，后续优化）

### 7.2 事务处理

- ⚠️ 确保事务正确提交或回滚
- ⚠️ 处理死锁情况（如需要）

### 7.3 性能优化

- ⚠️ 使用索引提高查询性能
- ⚠️ 考虑批量操作（如需要，后续优化）

---

## 八、后续任务

完成本任务后，可以继续：

- [ ] TODO: 高级压缩策略（阶段 4，P1）
- [ ] TODO: 检索功能和语义搜索（阶段 5，P1）

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 1.0  
**状态**: ⏳ 待开始

