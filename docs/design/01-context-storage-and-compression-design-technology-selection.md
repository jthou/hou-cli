# 上下文存储后端技术选型分析

## 概述

本文档分析 Memory、File、Database 三种存储后端的技术选型，提供具体实现建议。

---

## 一、Memory 存储后端

### 1.1 技术选型

**推荐方案**: Python 标准库（`collections.deque` + `dict`）

**理由**:
- ✅ **零依赖**: 使用 Python 标准库，无需额外安装
- ✅ **高性能**: 内存操作，速度最快
- ✅ **简单**: 实现简单，易于维护
- ✅ **适合 MVP**: 满足初期需求

### 1.2 实现细节

```python
from collections import deque
from typing import Dict
import uuid

class MemoryStorageBackend(StorageBackend):
    """内存存储后端（使用 Python 标准库）"""
    
    def __init__(self, max_messages_per_session: int = 100):
        self.max_messages_per_session = max_messages_per_session
        self.sessions: Dict[str, Session] = {}
        self.messages: Dict[str, deque] = {}  # 使用 deque 自动限制大小
```

**技术栈**:
- `collections.deque`: 双端队列，自动限制大小
- `dict`: 字典，用于存储会话和消息
- `uuid`: UUID 生成（标准库）

**优点**:
- 无需额外依赖
- 性能最优
- 实现简单

**缺点**:
- 数据不持久化（重启后丢失）
- 内存占用（不适合大量数据）

---

## 二、File 存储后端

### 2.1 技术选型对比

#### 方案 A: JSON 文件（推荐）

**技术栈**: Python 标准库 `json`

**优点**:
- ✅ **零依赖**: 标准库
- ✅ **可读性强**: 人类可读，易于调试
- ✅ **跨平台**: 所有平台支持
- ✅ **易于备份**: 文本文件，易于版本控制

**缺点**:
- ⚠️ **性能一般**: 每次读写需要序列化/反序列化
- ⚠️ **文件大小**: 文本格式，占用空间较大
- ⚠️ **并发限制**: 多进程写入需要锁机制

**适用场景**: 
- 单机部署
- 数据量中等（< 10万条消息）
- 需要可读性和可调试性

#### 方案 B: MessagePack（备选）

**技术栈**: `msgpack` 库

**优点**:
- ✅ **性能好**: 二进制格式，比 JSON 快
- ✅ **体积小**: 比 JSON 节省 20-30% 空间
- ✅ **类型支持**: 支持更多数据类型

**缺点**:
- ❌ **需要依赖**: 需要安装 `msgpack`
- ❌ **不可读**: 二进制格式，无法直接查看
- ❌ **调试困难**: 需要工具才能查看内容

**适用场景**:
- 性能要求高
- 数据量大
- 不需要人工查看文件内容

#### 方案 C: SQLite 文件数据库（备选）

**技术栈**: Python 标准库 `sqlite3`

**优点**:
- ✅ **零依赖**: 标准库
- ✅ **查询能力**: 支持 SQL 查询
- ✅ **性能好**: 数据库引擎优化
- ✅ **事务支持**: ACID 特性

**缺点**:
- ⚠️ **复杂度**: 比 JSON 文件复杂
- ⚠️ **文件锁定**: 并发访问需要处理

**适用场景**:
- 需要复杂查询
- 数据量大
- 需要事务支持

### 2.2 推荐方案

**推荐**: **JSON 文件**（方案 A）

**理由**:
1. **零依赖**: 使用标准库，符合项目轻量级原则
2. **可读性**: 便于调试和问题排查
3. **简单**: 实现简单，维护成本低
4. **足够**: 对于大多数场景，性能足够

**实现示例**:
```python
import json
from pathlib import Path

class FileStorageBackend(StorageBackend):
    """文件存储后端（JSON 格式）"""
    
    def __init__(self, storage_dir: Path = Path("data/contexts")):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # 使用 JSON 文件存储
```

**未来优化**:
- 如果性能成为瓶颈，可以迁移到 MessagePack
- 如果需要复杂查询，可以迁移到 SQLite 文件数据库

---

## 三、Database 存储后端

### 3.1 技术选型对比

#### 方案 A: SQLite（推荐）

**技术栈**: Python 标准库 `sqlite3`

**优点**:
- ✅ **零依赖**: Python 标准库
- ✅ **轻量级**: 单文件数据库，无需服务器
- ✅ **性能好**: 适合中小规模数据
- ✅ **事务支持**: ACID 特性
- ✅ **SQL 查询**: 支持复杂查询

**缺点**:
- ⚠️ **并发限制**: 写入并发性能有限
- ⚠️ **规模限制**: 不适合超大规模数据（> 100GB）

**适用场景**:
- 单机部署
- 中小规模数据（< 100GB）
- 需要 SQL 查询能力
- 需要事务支持

#### 方案 B: PostgreSQL（生产环境）

**技术栈**: `psycopg2` 或 `asyncpg`

**优点**:
- ✅ **功能强大**: 完整的关系型数据库
- ✅ **并发性能**: 支持高并发写入
- ✅ **扩展性**: 支持大规模数据
- ✅ **可靠性**: 生产级数据库

**缺点**:
- ❌ **需要依赖**: 需要安装 PostgreSQL 和驱动
- ❌ **复杂度**: 需要数据库服务器
- ❌ **资源占用**: 需要更多系统资源

**适用场景**:
- 生产环境
- 多设备同步
- 大规模数据
- 高并发需求

#### 方案 C: Redis（缓存/临时存储）

**技术栈**: `redis` 库

**优点**:
- ✅ **高性能**: 内存数据库，速度极快
- ✅ **数据结构**: 支持多种数据结构
- ✅ **分布式**: 支持集群和主从复制

**缺点**:
- ❌ **需要依赖**: 需要 Redis 服务器
- ❌ **持久化**: 默认不持久化（可配置）
- ❌ **成本**: 内存成本高

**适用场景**:
- 缓存场景
- 临时存储
- 高性能要求
- 分布式部署

### 3.2 推荐方案

**推荐**: **SQLite**（方案 A）

**理由**:
1. **零依赖**: 使用标准库，符合项目轻量级原则
2. **轻量级**: 单文件数据库，无需额外服务
3. **功能完整**: 支持 SQL 查询、事务、索引等
4. **性能足够**: 对于大多数场景，性能足够

**实现示例**:
```python
import sqlite3
from typing import Optional

class DatabaseStorageBackend(StorageBackend):
    """数据库存储后端（SQLite）"""
    
    def __init__(self, db_path: str = "data/contexts.db"):
        self.db_path = db_path
        self._init_db()  # 使用 sqlite3 标准库
```

**未来扩展**:
- 如果需要在生产环境部署，可以添加 PostgreSQL 支持
- 如果需要缓存，可以添加 Redis 支持

---

## 四、技术选型总结

### 4.1 推荐方案

| 存储类型 | 推荐技术 | 依赖 | 适用场景 |
|---------|---------|------|---------|
| **Memory** | `collections.deque` + `dict` | 无 | 临时存储、开发测试 |
| **File** | `json` (标准库) | 无 | 单机持久化、中小规模 |
| **Database** | `sqlite3` (标准库) | 无 | 需要查询、事务支持 |

### 4.2 技术栈依赖

**核心依赖**: **零依赖** ✅
- 所有推荐方案都使用 Python 标准库
- 无需安装额外包
- 符合项目轻量级原则

**可选依赖**（未来扩展）:
- `msgpack`: 如果 File 存储需要更高性能
- `psycopg2`: 如果需要 PostgreSQL 支持
- `redis`: 如果需要 Redis 支持

### 4.3 实现优先级

**阶段 1（P0）**: 使用标准库实现
- Memory: `deque` + `dict`
- File: `json`
- Database: `sqlite3`

**阶段 2（P1）**: 优化和扩展
- 如果性能需要，考虑 MessagePack
- 如果需要生产环境，考虑 PostgreSQL

---

## 五、性能对比

### 5.1 读写性能（相对值）

| 存储类型 | 读取速度 | 写入速度 | 查询能力 |
|---------|---------|---------|---------|
| Memory | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| File (JSON) | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| File (MessagePack) | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| SQLite | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| PostgreSQL | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 5.2 适用场景

**Memory**:
- 开发测试
- 临时会话
- 高性能要求

**File (JSON)**:
- 单机部署
- 中小规模（< 10万条消息）
- 需要可读性

**SQLite**:
- 单机部署
- 中大规模（< 100GB）
- 需要查询能力

**PostgreSQL**:
- 生产环境
- 大规模数据
- 多设备同步

---

## 六、实现建议

### 6.1 默认配置

```python
# 默认使用 Memory 存储（开发阶段）
context_manager = ContextManager()

# 生产环境使用 File 存储（JSON）
context_manager = ContextManager(
    storage_backend=FileStorageBackend(Path("data/contexts"))
)

# 需要查询能力时使用 SQLite
context_manager = ContextManager(
    storage_backend=DatabaseStorageBackend("data/contexts.db")
)
```

### 6.2 配置建议

**开发环境**:
- 使用 `MemoryStorageBackend`（快速、无需持久化）

**测试环境**:
- 使用 `FileStorageBackend`（可持久化、可查看）

**生产环境**:
- 小规模：`FileStorageBackend`（JSON）
- 中规模：`DatabaseStorageBackend`（SQLite）
- 大规模：`DatabaseStorageBackend`（PostgreSQL，未来扩展）

---

## 七、相关文档

- `docs/design/01-context-storage-and-compression-design.md` - 上下文存储设计
- `docs/design/03-dependency-management.md` - 依赖管理指南

---

**创建时间**: 2025-01-01  
**版本**: 1.0  
**状态**: 技术选型确定

