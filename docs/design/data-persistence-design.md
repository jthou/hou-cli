# 数据持久化设计方案

## 概述

本文档说明 SQLite 和 ChromaDB 的数据持久化方案，包括存储位置、配置方式、备份策略等。

## 一、数据存储位置

### 1.1 应用数据目录

使用 `shared/platform_utils.py` 中的 `get_app_data_dir()` 获取跨平台数据目录：

```python
# macOS
~/Library/Application Support/hou-cli/

# Linux
~/.local/share/hou-cli/

# Windows
%LOCALAPPDATA%\hou-cli\
```

### 1.2 目录结构

```
hou-cli/
├── databases/              # 数据库文件
│   ├── sessions.db        # SQLite: 会话历史
│   ├── contexts.db         # SQLite: 上下文缓存
│   └── metadata.db         # SQLite: 元数据
│
├── chroma/                 # ChromaDB 数据目录
│   ├── chroma.sqlite3      # ChromaDB 元数据（SQLite）
│   ├── collections/        # 集合数据
│   └── embeddings/         # 向量数据
│
├── config/                 # 配置文件
│   ├── config.json
│   └── settings.json
│
└── logs/                   # 日志文件
    └── app.log
```

## 二、SQLite 持久化

### 2.1 持久化方式

SQLite 是**文件数据库**，数据直接存储在 `.db` 文件中，**默认就是持久化的**。

```python
import sqlite3
from pathlib import Path
from shared.platform_utils import get_app_data_dir

# 获取数据目录
data_dir = get_app_data_dir() / "databases"
data_dir.mkdir(parents=True, exist_ok=True)

# 连接数据库（自动创建文件）
db_path = data_dir / "sessions.db"
conn = sqlite3.connect(str(db_path))

# 数据会自动持久化到文件
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data TEXT
    )
""")
conn.commit()  # 提交事务，数据写入磁盘
conn.close()
```

### 2.2 持久化特性

**自动持久化**：
- ✅ 每次 `commit()` 后数据立即写入磁盘
- ✅ 关闭连接时自动提交未提交的事务
- ✅ 支持 WAL 模式（Write-Ahead Logging）提高性能

**配置选项**：

```python
# 使用 WAL 模式（推荐，提高并发性能）
conn.execute("PRAGMA journal_mode=WAL")

# 设置同步模式（平衡性能和安全性）
conn.execute("PRAGMA synchronous=NORMAL")  # 或 FULL（更安全）

# 设置缓存大小（提高性能）
conn.execute("PRAGMA cache_size=-64000")  # 64MB 缓存
```

### 2.3 实现示例

```python
"""SQLite 持久化实现"""
import sqlite3
from pathlib import Path
from typing import Optional
from shared.platform_utils import get_app_data_dir

class SQLiteStorage:
    """SQLite 存储管理器"""
    
    def __init__(self, db_name: str = "sessions.db"):
        self.data_dir = get_app_data_dir() / "databases"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / db_name
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(str(self.db_path))
        # 启用 WAL 模式
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        
        # 创建表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def save(self, session_id: str, data: dict):
        """保存会话数据"""
        import json
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO sessions (id, data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (session_id, json.dumps(data)))
        conn.commit()  # 立即持久化到磁盘
        conn.close()
    
    def load(self, session_id: str) -> Optional[dict]:
        """加载会话数据"""
        import json
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT data FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None
```

## 三、ChromaDB 持久化

### 3.1 持久化方式

ChromaDB 使用 `PersistentClient` 实现持久化，数据存储在指定目录中。

```python
import chromadb
from pathlib import Path
from shared.platform_utils import get_app_data_dir

# 获取数据目录
data_dir = get_app_data_dir() / "chroma"
data_dir.mkdir(parents=True, exist_ok=True)

# 创建持久化客户端
client = chromadb.PersistentClient(path=str(data_dir))

# 创建或获取集合
collection = client.get_or_create_collection(
    name="knowledge_base",
    metadata={"description": "知识库向量存储"}
)

# 添加数据（自动持久化）
collection.add(
    documents=["文档内容"],
    ids=["doc1"],
    embeddings=[[0.1, 0.2, 0.3]]  # 向量
)
# 数据立即持久化到磁盘
```

### 3.2 持久化特性

**自动持久化**：
- ✅ 每次操作（add/update/delete）后自动持久化
- ✅ 使用 SQLite 存储元数据
- ✅ 向量数据存储在磁盘文件中
- ✅ 支持增量更新

**存储结构**：

```
chroma/
├── chroma.sqlite3          # 元数据（SQLite）
├── collections/            # 集合数据
│   └── knowledge_base/
│       ├── data_level0.bin # 向量数据
│       └── metadata.json  # 集合元数据
└── embeddings/             # 嵌入缓存
```

### 3.3 实现示例

```python
"""ChromaDB 持久化实现"""
import chromadb
from pathlib import Path
from typing import List, Dict, Optional
from shared.platform_utils import get_app_data_dir

class ChromaDBStorage:
    """ChromaDB 存储管理器"""
    
    def __init__(self, collection_name: str = "knowledge_base"):
        self.data_dir = get_app_data_dir() / "chroma"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建持久化客户端
        self.client = chromadb.PersistentClient(path=str(self.data_dir))
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "知识库向量存储"}
        )
    
    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        ids: List[str],
        metadatas: Optional[List[Dict]] = None
    ):
        """添加文档（自动持久化）"""
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        # 数据已自动持久化到磁盘
    
    def search(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10
    ) -> Dict:
        """搜索相似文档"""
        return self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results
        )
    
    def delete(self, ids: List[str]):
        """删除文档（自动持久化）"""
        self.collection.delete(ids=ids)
        # 删除操作已自动持久化
```

## 四、统一存储管理器

### 4.1 实现

```python
"""统一存储管理器"""
from pathlib import Path
from typing import Optional
from shared.platform_utils import get_app_data_dir
import sqlite3
import chromadb
import json

class StorageManager:
    """统一存储管理器"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite 数据库目录
        self.db_dir = self.data_dir / "databases"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # ChromaDB 数据目录
        self.chroma_dir = self.data_dir / "chroma"
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 SQLite
        self._init_sqlite()
        
        # 初始化 ChromaDB
        self._init_chromadb()
    
    def _init_sqlite(self):
        """初始化 SQLite"""
        db_path = self.db_dir / "sessions.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def _init_chromadb(self):
        """初始化 ChromaDB"""
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_dir)
        )
        self.knowledge_collection = self.chroma_client.get_or_create_collection(
            name="knowledge_base"
        )
    
    def get_sqlite_connection(self, db_name: str = "sessions.db"):
        """获取 SQLite 连接"""
        db_path = self.db_dir / db_name
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    def get_chroma_collection(self, collection_name: str = "knowledge_base"):
        """获取 ChromaDB 集合"""
        return self.chroma_client.get_or_create_collection(
            name=collection_name
        )
    
    def get_data_dir(self) -> Path:
        """获取数据目录"""
        return self.data_dir
```

## 五、备份策略

### 5.1 备份方案

```python
"""数据备份工具"""
from pathlib import Path
import shutil
from datetime import datetime
from shared.platform_utils import get_app_data_dir

class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.data_dir = get_app_data_dir()
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_all(self):
        """备份所有数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # 备份 SQLite 数据库
        db_dir = self.data_dir / "databases"
        if db_dir.exists():
            shutil.copytree(db_dir, backup_path / "databases")
        
        # 备份 ChromaDB 数据
        chroma_dir = self.data_dir / "chroma"
        if chroma_dir.exists():
            shutil.copytree(chroma_dir, backup_path / "chroma")
        
        # 备份配置文件
        config_dir = self.data_dir / "config"
        if config_dir.exists():
            shutil.copytree(config_dir, backup_path / "config")
        
        return backup_path
    
    def restore(self, backup_path: Path):
        """恢复备份"""
        # 停止服务
        # ...
        
        # 恢复数据
        if (backup_path / "databases").exists():
            shutil.copytree(
                backup_path / "databases",
                self.data_dir / "databases",
                dirs_exist_ok=True
            )
        
        if (backup_path / "chroma").exists():
            shutil.copytree(
                backup_path / "chroma",
                self.data_dir / "chroma",
                dirs_exist_ok=True
            )
```

## 六、配置示例

### 6.1 环境变量配置

```bash
# .env 文件
# 数据目录（可选，默认使用 get_app_data_dir()）
DATA_DIR=/path/to/custom/data/dir

# SQLite 配置
SQLITE_DB_PATH=databases/sessions.db
SQLITE_WAL_MODE=true
SQLITE_SYNC_MODE=NORMAL

# ChromaDB 配置
CHROMA_DB_PATH=chroma
CHROMA_COLLECTION_NAME=knowledge_base
```

### 6.2 代码配置

```python
"""配置管理"""
from pathlib import Path
import os
from shared.platform_utils import get_app_data_dir

class Config:
    """配置类"""
    
    # 数据目录
    DATA_DIR = Path(os.getenv("DATA_DIR", str(get_app_data_dir())))
    
    # SQLite 配置
    SQLITE_DB_DIR = DATA_DIR / "databases"
    SQLITE_WAL_MODE = os.getenv("SQLITE_WAL_MODE", "true").lower() == "true"
    SQLITE_SYNC_MODE = os.getenv("SQLITE_SYNC_MODE", "NORMAL")
    
    # ChromaDB 配置
    CHROMA_DB_DIR = DATA_DIR / "chroma"
    CHROMA_COLLECTION_NAME = os.getenv(
        "CHROMA_COLLECTION_NAME",
        "knowledge_base"
    )
```

## 七、最佳实践

### 7.1 SQLite 最佳实践

1. **使用 WAL 模式**
   ```python
   conn.execute("PRAGMA journal_mode=WAL")
   ```

2. **定期 VACUUM**
   ```python
   conn.execute("VACUUM")  # 清理和优化数据库
   ```

3. **使用事务**
   ```python
   conn.execute("BEGIN")
   # 多个操作
   conn.commit()  # 或 conn.rollback()
   ```

4. **连接池管理**
   ```python
   # 使用连接池或单例模式管理连接
   ```

### 7.2 ChromaDB 最佳实践

1. **批量操作**
   ```python
   # 批量添加，减少 I/O
   collection.add(documents=[...], ids=[...], embeddings=[...])
   ```

2. **定期清理**
   ```python
   # 删除不需要的文档
   collection.delete(ids=[...])
   ```

3. **集合管理**
   ```python
   # 为不同用途创建不同集合
   knowledge_collection = client.get_or_create_collection("knowledge")
   cache_collection = client.get_or_create_collection("cache")
   ```

## 八、总结

### 持久化特性

| 数据库 | 持久化方式 | 自动持久化 | 存储位置 |
|--------|-----------|-----------|---------|
| **SQLite** | 文件数据库 | ✅ 是（commit 后） | `databases/*.db` |
| **ChromaDB** | 文件存储 | ✅ 是（操作后） | `chroma/` |

### 关键点

1. **SQLite**：
   - 使用 `sqlite3.connect()` 连接文件
   - 每次 `commit()` 后数据写入磁盘
   - 推荐使用 WAL 模式

2. **ChromaDB**：
   - 使用 `PersistentClient(path=...)` 创建客户端
   - 所有操作自动持久化
   - 数据存储在指定目录

3. **数据目录**：
   - 使用 `get_app_data_dir()` 获取跨平台目录
   - 自动创建目录结构
   - 数据不会丢失（除非手动删除）
