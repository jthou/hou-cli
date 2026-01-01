# 长期记忆模块技术选型分析

## 概述

本文档分析长期记忆模块中三个核心组件的技术选型：
1. **Memory Store（持久化存储）**：存储记忆的原始数据
2. **Vector Store（语义搜索）**：存储向量嵌入，支持语义搜索
3. **Index Store（索引管理）**：管理记忆的索引和元数据

---

## 一、Memory Store（持久化存储）技术选型

### 1.1 需求分析

**功能需求**:
- 存储记忆的完整内容（文本、元数据）
- 支持快速读写
- 持久化存储（重启不丢失）
- 支持查询和过滤

### 1.2 技术选型对比

#### 方案 A: JSON 文件（推荐）

**技术栈**: Python 标准库 `json`

**优点**:
- ✅ **零依赖**: 标准库
- ✅ **可读性强**: 人类可读，易于调试
- ✅ **简单**: 实现简单，维护成本低
- ✅ **跨平台**: 所有平台支持

**缺点**:
- ⚠️ **性能一般**: 大量数据时读写较慢
- ⚠️ **文件大小**: 文本格式占用空间

**适用场景**:
- 中小规模数据（< 10万条记忆）
- 需要可读性和可调试性
- 单机部署

#### 方案 B: SQLite 数据库（备选）

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
- 中大规模数据（< 100GB）
- 需要复杂查询
- 需要事务支持

#### 方案 C: MessagePack（高性能备选）

**技术栈**: `msgpack` 库

**优点**:
- ✅ **性能好**: 二进制格式，比 JSON 快
- ✅ **体积小**: 比 JSON 节省 20-30% 空间

**缺点**:
- ❌ **需要依赖**: 需要安装 `msgpack`
- ❌ **不可读**: 二进制格式，无法直接查看

**适用场景**:
- 性能要求高
- 数据量大
- 不需要人工查看

### 1.3 推荐方案

**推荐**: **JSON 文件**（方案 A）

**理由**:
1. **零依赖**: 符合项目轻量级原则
2. **可读性**: 便于调试和问题排查
3. **足够**: 对于大多数场景，性能足够
4. **一致性**: 与 FileStorageBackend 保持一致

**未来扩展**:
- 如果性能成为瓶颈，可以迁移到 SQLite
- 如果需要复杂查询，可以迁移到 SQLite

---

## 二、Vector Store（语义搜索）技术选型

### 2.1 需求分析

**功能需求**:
- 存储文本的向量嵌入（embeddings）
- 支持相似度搜索（语义搜索）
- 支持元数据过滤
- 高性能查询

### 2.2 技术选型对比

#### 方案 A: Chroma（推荐）⭐

**技术栈**: `chromadb` 库

**优点**:
- ✅ **轻量级**: 单文件数据库，无需服务器
- ✅ **易用**: API 简单，易于集成
- ✅ **功能完整**: 支持元数据过滤、持久化
- ✅ **性能好**: 适合中小规模数据
- ✅ **项目已有**: 设计文档中已提到 Chroma

**缺点**:
- ⚠️ **需要依赖**: 需要安装 `chromadb`
- ⚠️ **规模限制**: 不适合超大规模（> 1000万向量）

**适用场景**:
- 中小规模向量数据（< 1000万向量）
- 单机部署
- 需要简单易用的 API

**安装**:
```bash
pip install chromadb
```

#### 方案 B: FAISS（高性能）

**技术栈**: `faiss-cpu` 或 `faiss-gpu`

**优点**:
- ✅ **性能极佳**: Facebook 开发，性能最优
- ✅ **灵活**: 支持多种索引算法
- ✅ **无服务器**: 单机运行

**缺点**:
- ❌ **需要依赖**: 需要安装 `faiss-cpu` 或 `faiss-gpu`
- ❌ **复杂度**: API 相对复杂
- ❌ **无持久化**: 需要手动实现持久化
- ❌ **无元数据**: 不支持元数据过滤（需要额外实现）

**适用场景**:
- 大规模向量数据（> 1000万向量）
- 性能要求极高
- 不需要元数据过滤

**安装**:
```bash
pip install faiss-cpu  # CPU 版本
# 或
pip install faiss-gpu  # GPU 版本（需要 CUDA）
```

#### 方案 C: Qdrant（生产环境）

**技术栈**: `qdrant-client` + Qdrant 服务器

**优点**:
- ✅ **功能强大**: 完整的向量数据库
- ✅ **高性能**: 适合生产环境
- ✅ **分布式**: 支持集群部署
- ✅ **REST API**: 支持 HTTP API

**缺点**:
- ❌ **需要服务器**: 需要运行 Qdrant 服务器
- ❌ **复杂度**: 需要管理服务器
- ❌ **资源占用**: 需要更多系统资源

**适用场景**:
- 生产环境
- 大规模数据
- 需要分布式部署

**安装**:
```bash
# 使用 Docker
docker run -p 6333:6333 qdrant/qdrant

# Python 客户端
pip install qdrant-client
```

#### 方案 D: 不使用向量存储（简单方案）

**技术栈**: 仅使用关键词搜索

**优点**:
- ✅ **零依赖**: 无需额外库
- ✅ **简单**: 实现简单

**缺点**:
- ❌ **无语义搜索**: 只能关键词匹配
- ❌ **效果差**: 搜索效果不如向量搜索

**适用场景**:
- 初期开发
- 不需要语义搜索
- 数据量很小

### 2.3 推荐方案

**推荐**: **Chroma**（方案 A）⭐

**理由**:
1. **项目已有**: 设计文档中已提到 Chroma
2. **易用性**: API 简单，易于集成
3. **功能完整**: 支持元数据过滤、持久化
4. **性能足够**: 对于大多数场景，性能足够
5. **轻量级**: 单文件数据库，无需服务器

**实现示例**:
```python
import chromadb
from chromadb.config import Settings

class ChromaVectorStore:
    def __init__(self, persist_directory: str = "data/vector_store"):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="long_term_memory",
            metadata={"description": "长期记忆向量存储"}
        )
```

**未来扩展**:
- 如果数据量超大，可以迁移到 FAISS
- 如果需要生产环境，可以迁移到 Qdrant

---

## 三、Index Store（索引管理）技术选型

### 3.1 需求分析

**功能需求**:
- 存储记忆的索引信息（ID、类型、标签、时间等）
- 支持快速查询和过滤
- 支持统计信息（访问次数、最后访问时间等）

### 3.2 技术选型对比

#### 方案 A: JSON 文件（推荐）

**技术栈**: Python 标准库 `json`

**优点**:
- ✅ **零依赖**: 标准库
- ✅ **可读性强**: 人类可读，易于调试
- ✅ **简单**: 实现简单，维护成本低
- ✅ **一致性**: 与 Memory Store 保持一致

**缺点**:
- ⚠️ **性能一般**: 大量数据时查询较慢
- ⚠️ **无索引**: 需要全量加载到内存

**适用场景**:
- 中小规模数据（< 10万条记忆）
- 需要可读性和可调试性

**实现示例**:
```python
import json
from pathlib import Path

class JSONIndexStore:
    def __init__(self, index_file: Path = Path("data/long_term_memory/index.json")):
        self.index_file = index_file
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"memories": {}}
    
    def _save_index(self):
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
```

#### 方案 B: SQLite 数据库（备选）

**技术栈**: Python 标准库 `sqlite3`

**优点**:
- ✅ **零依赖**: 标准库
- ✅ **查询能力**: 支持 SQL 查询和索引
- ✅ **性能好**: 数据库引擎优化
- ✅ **事务支持**: ACID 特性

**缺点**:
- ⚠️ **复杂度**: 比 JSON 文件复杂
- ⚠️ **文件锁定**: 并发访问需要处理

**适用场景**:
- 中大规模数据（< 100GB）
- 需要复杂查询
- 需要事务支持

**实现示例**:
```python
import sqlite3

class SQLiteIndexStore:
    def __init__(self, db_path: str = "data/long_term_memory/index.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_index (
                memory_id TEXT PRIMARY KEY,
                memory_type TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_type ON memory_index(memory_type)
        """)
        
        conn.commit()
        conn.close()
```

#### 方案 C: 内存索引（高性能）

**技术栈**: Python 标准库 `dict` + `set`

**优点**:
- ✅ **零依赖**: 标准库
- ✅ **性能极佳**: 内存操作，速度最快
- ✅ **简单**: 实现简单

**缺点**:
- ❌ **不持久化**: 重启后丢失（需要配合持久化存储）

**适用场景**:
- 作为缓存层
- 配合持久化存储使用

### 3.3 推荐方案

**推荐**: **JSON 文件**（方案 A）

**理由**:
1. **零依赖**: 符合项目轻量级原则
2. **一致性**: 与 Memory Store 保持一致
3. **可读性**: 便于调试和问题排查
4. **足够**: 对于大多数场景，性能足够

**未来扩展**:
- 如果性能成为瓶颈，可以迁移到 SQLite
- 如果需要复杂查询，可以迁移到 SQLite

---

## 四、技术选型总结

### 4.1 推荐方案

| 组件 | 推荐技术 | 依赖 | 适用场景 |
|------|---------|------|---------|
| **Memory Store** | `json` (标准库) | 无 | 中小规模，需要可读性 |
| **Vector Store** | `chromadb` | 需要 | 语义搜索，中小规模 |
| **Index Store** | `json` (标准库) | 无 | 中小规模，需要可读性 |

### 4.2 依赖总结

**必需依赖**:
- `chromadb`: 向量存储和语义搜索

**可选依赖**（未来扩展）:
- `faiss-cpu`: 如果向量数据量超大
- `qdrant-client`: 如果需要生产环境部署
- `msgpack`: 如果 Memory Store 需要更高性能
- `sqlite3`: 如果 Index Store 需要复杂查询（标准库，无需安装）

### 4.3 架构设计

```
LongTermMemory
├── Memory Store (JSON 文件)
│   └── 存储记忆的完整内容
├── Vector Store (Chroma)
│   └── 存储向量嵌入，支持语义搜索
└── Index Store (JSON 文件)
    └── 存储索引和元数据
```

### 4.4 实现优先级

**阶段 1（P0）**: 基础实现
- Memory Store: JSON 文件
- Index Store: JSON 文件
- Vector Store: 暂不实现（使用关键词搜索）

**阶段 2（P1）**: 语义搜索
- Vector Store: Chroma 实现
- 向量嵌入生成（需要 embedding 模型）

**阶段 3（P2）**: 性能优化
- 如果性能需要，考虑 SQLite（Index Store）
- 如果向量数据量大，考虑 FAISS

---

## 五、Chroma 集成示例

### 5.1 基本使用

```python
import chromadb
from chromadb.config import Settings

class ChromaVectorStore:
    """Chroma 向量存储"""
    
    def __init__(self, persist_directory: str = "data/vector_store"):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="long_term_memory",
            metadata={"description": "长期记忆向量存储"}
        )
    
    def add_memory(self, memory_id: str, content: str, embedding: List[float], metadata: Dict):
        """添加记忆向量"""
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )
    
    def search(self, query_embedding: List[float], top_k: int = 10, filter: Dict = None):
        """搜索相似记忆"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter
        )
        return results
```

### 5.2 与长期记忆集成

```python
class VectorLongTermMemory(LongTermMemory):
    """带向量搜索的长期记忆"""
    
    def __init__(
        self,
        storage_dir: Path = Path("data/long_term_memory"),
        vector_store: Optional[ChromaVectorStore] = None,
        embedding_model = None
    ):
        # Memory Store
        self.memory_store = FileMemoryStore(storage_dir / "memories")
        
        # Index Store
        self.index_store = JSONIndexStore(storage_dir / "index.json")
        
        # Vector Store
        self.vector_store = vector_store or ChromaVectorStore(
            persist_directory=str(storage_dir / "vector_store")
        )
        
        # Embedding 模型
        self.embedding_model = embedding_model
    
    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 10
    ) -> List[Memory]:
        """使用向量搜索记忆"""
        # 生成查询向量
        query_embedding = self.embedding_model.embed_query(query)
        
        # 构建过滤条件
        filter_dict = {}
        if memory_type:
            filter_dict["memory_type"] = memory_type.value
        
        # 向量搜索
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter=filter_dict if filter_dict else None
        )
        
        # 获取完整记忆
        memories = []
        for memory_id in results["ids"][0]:
            memory = self.memory_store.get_memory(memory_id)
            if memory:
                memories.append(memory)
        
        return memories
```

---

## 六、相关文档

- `docs/design/01-context-storage-and-compression-design.md` - 上下文存储设计
- `docs/design/01-knowledge-base-design.md` - 知识库设计（包含 VectorStore）
- `docs/design/03-dependency-management.md` - 依赖管理指南

---

**创建时间**: 2025-01-01  
**版本**: 1.0  
**状态**: 技术选型确定

