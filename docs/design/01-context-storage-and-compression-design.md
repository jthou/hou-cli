# 上下文存储和整理机制设计

## 概述

本文档设计一个**独立、可复用、可扩展**的上下文管理模块，支持多种存储后端、压缩策略和检索方式。该模块可以作为独立组件被不同的 Agent 使用。

**设计目标**:
- ✅ **独立性**: 模块化设计，不依赖特定业务逻辑
- ✅ **可复用性**: 可被多个 Agent 或服务使用
- ✅ **可扩展性**: 支持插件化的存储后端和压缩策略
- ✅ **灵活性**: 支持多种使用场景（单会话、多会话、跨设备等）
- ✅ **性能**: 支持内存缓存、批量操作、异步处理
- ✅ **持久化**: 默认支持持久化存储，数据不丢失
- ✅ **长期记忆**: 支持跨会话的长期记忆存储和检索

**创建时间**: 2025-01-01  
**状态**: 设计阶段  
**优先级**: 中高（作为独立模块，需要完整设计）

---

## 一、模块架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    ContextManager                        │
│                  (统一接口层)                            │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Storage      │  │ Compression  │  │ Retrieval    │  │
│  │ Backend      │  │ Strategy    │  │ Engine       │  │
│  │ (可插拔)      │  │ (可插拔)     │  │ (可插拔)      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │         │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐    │
│  │ Memory      │  │ TimeWindow   │  │ Keyword     │    │
│  │ File ✅     │  │ TokenLimit   │  │ Semantic    │    │
│  │ Database ✅ │  │ Importance   │  │ Vector      │    │
│  └─────────────┘  └──────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              LongTermMemory (长期记忆)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Memory Store  │  │ Vector Store │  │ Index Store  │  │
│  │ (持久化)      │  │ (语义搜索)    │  │ (索引管理)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

1. **ContextManager**: 统一接口层，提供高级 API
2. **StorageBackend**: 存储后端接口，支持多种实现
3. **CompressionStrategy**: 压缩策略接口，支持多种算法
4. **RetrievalEngine**: 检索引擎接口，支持多种检索方式
5. **Message**: 消息数据模型
6. **Session**: 会话数据模型

---

## 二、数据模型设计

### 2.1 Message（消息）

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class Message:
    """消息数据模型"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            message_id=data.get("message_id")
        )
```

### 2.2 Session（会话）

```python
@dataclass
class Session:
    """会话数据模型"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """从字典创建"""
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {})
        )
```

---

## 三、存储后端设计（可插拔）

### 3.1 StorageBackend 接口

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

class StorageBackend(ABC):
    """存储后端接口"""
    
    @abstractmethod
    def save_message(self, session_id: str, message: Message) -> bool:
        """保存消息"""
        pass
    
    @abstractmethod
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """获取消息列表"""
        pass
    
    @abstractmethod
    def delete_message(self, session_id: str, message_id: str) -> bool:
        """删除消息"""
        pass
    
    @abstractmethod
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        pass
    
    @abstractmethod
    def create_session(self, session: Session) -> bool:
        """创建会话"""
        pass
    
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        pass
    
    @abstractmethod
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        pass
```

### 3.2 MemoryStorageBackend（内存存储）

**技术栈**: Python 标准库（`collections.deque` + `dict`）

**优点**:
- ✅ 零依赖（标准库）
- ✅ 性能最优（内存操作）
- ✅ 实现简单

**缺点**:
- ❌ 数据不持久化（重启后丢失）
- ❌ 内存占用（不适合大量数据）

```python
from collections import deque
from typing import Dict
import uuid

class MemoryStorageBackend(StorageBackend):
    """内存存储后端（默认）"""
    
    def __init__(self, max_messages_per_session: int = 100):
        self.max_messages_per_session = max_messages_per_session
        self.sessions: Dict[str, Session] = {}
        self.messages: Dict[str, deque] = {}  # {session_id: deque([Message])}
    
    def save_message(self, session_id: str, message: Message) -> bool:
        """保存消息"""
        if session_id not in self.messages:
            self.messages[session_id] = deque(maxlen=self.max_messages_per_session)
        
        if not message.message_id:
            message.message_id = str(uuid.uuid4())
        
        self.messages[session_id].append(message)
        
        # 更新会话时间
        if session_id in self.sessions:
            self.sessions[session_id].updated_at = datetime.now()
        
        return True
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """获取消息列表"""
        if session_id not in self.messages:
            return []
        
        messages = list(self.messages[session_id])
        
        # 应用 offset 和 limit
        if offset > 0:
            messages = messages[offset:]
        if limit:
            messages = messages[:limit]
        
        return messages
    
    def delete_message(self, session_id: str, message_id: str) -> bool:
        """删除消息"""
        if session_id not in self.messages:
            return False
        
        messages = list(self.messages[session_id])
        for i, msg in enumerate(messages):
            if msg.message_id == message_id:
                self.messages[session_id] = deque(
                    messages[:i] + messages[i+1:],
                    maxlen=self.max_messages_per_session
                )
                return True
        
        return False
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        if session_id in self.messages:
            self.messages[session_id].clear()
        if session_id in self.sessions:
            del self.sessions[session_id]
        return True
    
    def create_session(self, session: Session) -> bool:
        """创建会话"""
        self.sessions[session.session_id] = session
        self.messages[session.session_id] = deque(maxlen=self.max_messages_per_session)
        return True
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        sessions = list(self.sessions.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        if limit:
            sessions = sessions[:limit]
        return sessions
```

### 3.3 FileStorageBackend（文件存储）

**技术栈**: Python 标准库 `json`

**优点**:
- ✅ 零依赖（标准库）
- ✅ 可读性强（人类可读）
- ✅ 易于调试和备份

**缺点**:
- ⚠️ 性能一般（需要序列化/反序列化）
- ⚠️ 文件大小（文本格式占用空间）

**备选方案**:
- MessagePack（需要 `msgpack` 库，性能更好但不可读）
- SQLite 文件数据库（需要复杂查询时）

```python
import json
from pathlib import Path

class FileStorageBackend(StorageBackend):
    """文件存储后端"""
    
    def __init__(self, storage_dir: Path = Path("data/contexts")):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions.json"
        self._load_sessions()
    
    def _get_session_dir(self, session_id: str) -> Path:
        """获取会话目录"""
        return self.storage_dir / session_id
    
    def _get_messages_file(self, session_id: str) -> Path:
        """获取消息文件"""
        return self._get_session_dir(session_id) / "messages.json"
    
    def _load_sessions(self):
        """加载会话列表"""
        if self.sessions_file.exists():
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.sessions = {
                    s["session_id"]: Session.from_dict(s)
                    for s in data.get("sessions", [])
                }
        else:
            self.sessions = {}
    
    def _save_sessions(self):
        """保存会话列表"""
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump({
                "sessions": [s.to_dict() for s in self.sessions.values()]
            }, f, ensure_ascii=False, indent=2)
    
    def save_message(self, session_id: str, message: Message) -> bool:
        """保存消息"""
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        
        messages_file = self._get_messages_file(session_id)
        
        # 加载现有消息
        messages = []
        if messages_file.exists():
            with open(messages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                messages = [Message.from_dict(m) for m in data.get("messages", [])]
        
        # 添加新消息
        if not message.message_id:
            message.message_id = str(uuid.uuid4())
        messages.append(message)
        
        # 保存消息
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump({
                "messages": [m.to_dict() for m in messages]
            }, f, ensure_ascii=False, indent=2)
        
        # 更新会话时间
        if session_id in self.sessions:
            self.sessions[session_id].updated_at = datetime.now()
            self._save_sessions()
        
        return True
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """获取消息列表"""
        messages_file = self._get_messages_file(session_id)
        
        if not messages_file.exists():
            return []
        
        with open(messages_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = [Message.from_dict(m) for m in data.get("messages", [])]
        
        # 应用 offset 和 limit
        if offset > 0:
            messages = messages[offset:]
        if limit:
            messages = messages[:limit]
        
        return messages
    
    def delete_message(self, session_id: str, message_id: str) -> bool:
        """删除消息"""
        messages_file = self._get_messages_file(session_id)
        
        if not messages_file.exists():
            return False
        
        with open(messages_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = [Message.from_dict(m) for m in data.get("messages", [])]
        
        # 删除消息
        original_count = len(messages)
        messages = [m for m in messages if m.message_id != message_id]
        
        if len(messages) < original_count:
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "messages": [m.to_dict() for m in messages]
                }, f, ensure_ascii=False, indent=2)
        return True
        
        return False
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        session_dir = self._get_session_dir(session_id)
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
        
        return True
    
    def create_session(self, session: Session) -> bool:
        """创建会话"""
        self.sessions[session.session_id] = session
        self._save_sessions()
        return True
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        sessions = list(self.sessions.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        if limit:
            sessions = sessions[:limit]
        return sessions
```

### 3.4 DatabaseStorageBackend（数据库存储）

**技术栈**: Python 标准库 `sqlite3`

**优点**:
- ✅ 零依赖（标准库）
- ✅ 轻量级（单文件数据库）
- ✅ 支持 SQL 查询和事务
- ✅ 性能好（适合中小规模）

**缺点**:
- ⚠️ 并发写入性能有限
- ⚠️ 不适合超大规模数据（> 100GB）

**备选方案**:
- PostgreSQL（生产环境，需要 `psycopg2` 或 `asyncpg`）
- Redis（缓存场景，需要 `redis` 库）

```python
import sqlite3
from typing import Optional

class DatabaseStorageBackend(StorageBackend):
    """数据库存储后端（SQLite）"""
    
    def __init__(self, db_path: str = "data/contexts.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # 创建消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
    
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id 
            ON messages(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
            ON messages(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def save_message(self, session_id: str, message: Message) -> bool:
        """保存消息"""
        if not message.message_id:
            message.message_id = str(uuid.uuid4())
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO messages 
                (message_id, session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message.message_id,
                session_id,
                message.role.value,
                message.content,
                message.timestamp.isoformat(),
                json.dumps(message.metadata)
            ))
        
        # 更新会话时间
            cursor.execute("""
                UPDATE sessions SET updated_at = ? WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """获取消息列表"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        query = """
            SELECT message_id, role, content, timestamp, metadata
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """
        
        params = [session_id]
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append(Message(
                message_id=row[0],
                role=MessageRole(row[1]),
                content=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                metadata=json.loads(row[4] if row[4] else "{}")
            ))
        
        return messages
    
    def delete_message(self, session_id: str, message_id: str) -> bool:
        """删除消息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        
        return True
    
    def create_session(self, session: Session) -> bool:
        """创建会话"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sessions 
            (session_id, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?)
        """, (
            session.session_id,
            session.created_at.isoformat(),
            session.updated_at.isoformat(),
            json.dumps(session.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, created_at, updated_at, metadata
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Session(
                session_id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                metadata=json.loads(row[3] if row[3] else "{}")
            )
        
        return None
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        query = "SELECT session_id, created_at, updated_at, metadata FROM sessions ORDER BY updated_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            sessions.append(Session(
                session_id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                metadata=json.loads(row[3] if row[3] else "{}")
            ))
        
        return sessions
```

---

## 四、压缩策略设计（可插拔）

### 4.1 CompressionStrategy 接口

```python
class CompressionStrategy(ABC):
    """压缩策略接口"""
    
    @abstractmethod
    def compress(
    self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """压缩消息列表"""
        pass
```

### 4.2 TimeWindowCompression（时间窗口压缩）

```python
class TimeWindowCompression(CompressionStrategy):
    """时间窗口压缩（保留最近的消息）"""
    
    def compress(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """压缩消息列表"""
        if max_messages and len(messages) > max_messages:
            return messages[-max_messages:]
        return messages
```

### 4.3 TokenLimitCompression（Token 限制压缩）

```python
class TokenLimitCompression(CompressionStrategy):
    """Token 限制压缩"""
    
    def __init__(self, tokenizer=None):
        self.tokenizer = tokenizer or self._default_tokenizer
    
    def _default_tokenizer(self, text: str) -> int:
        """默认 tokenizer（简单估算：1 token ≈ 4 字符）"""
            return len(text) // 4
    
    def compress(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """压缩消息列表"""
        if not max_tokens:
            if max_messages:
                return messages[-max_messages:] if max_messages else messages
            return messages
    
    # 计算总 token 数
        total_tokens = sum(self.tokenizer(msg.content) for msg in messages)
    
    if total_tokens <= max_tokens:
            return messages
    
        # 策略：优先保留系统消息，然后从后往前保留
    compressed = []
    tokens_used = 0
    
    # 1. 优先保留系统消息
        system_messages = [msg for msg in messages if msg.role == MessageRole.SYSTEM]
        for msg in system_messages:
            tokens = self.tokenizer(msg.content)
            if tokens_used + tokens <= max_tokens:
                compressed.append(msg)
                tokens_used += tokens
    
        # 2. 从后往前保留其他消息
        other_messages = [msg for msg in messages if msg.role != MessageRole.SYSTEM]
        for msg in reversed(other_messages):
            tokens = self.tokenizer(msg.content)
        if tokens_used + tokens <= max_tokens:
                compressed.insert(len(compressed) - len(system_messages), msg)
            tokens_used += tokens
        else:
            break
    
    return compressed
```

### 4.4 ImportanceScoringCompression（重要性评分压缩）

```python
class ImportanceScoringCompression(CompressionStrategy):
    """重要性评分压缩"""
    
    def __init__(self, tokenizer=None):
        self.tokenizer = tokenizer or (lambda text: len(text) // 4)
    
    def _calculate_importance(self, message: Message, all_messages: List[Message]) -> float:
    """计算消息重要性分数"""
    score = 0.0
    
    # 系统消息重要性高
        if message.role == MessageRole.SYSTEM:
        score += 10.0
    
    # 最近的消息重要性高
        if message in all_messages[-5:]:
        score += 5.0
    
    # 包含关键词的消息重要性高
        important_keywords = ["错误", "问题", "重要", "关键", "失败", "异常"]
        content_lower = message.content.lower()
    for keyword in important_keywords:
            if keyword in content_lower:
            score += 2.0
    
        # 用户消息通常比助手消息重要
        if message.role == MessageRole.USER:
            score += 1.0
        
    return score
    
    def compress(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """压缩消息列表"""
        if max_messages and len(messages) <= max_messages:
            if not max_tokens:
                return messages
        
        # 计算每条消息的重要性分数
        scored_messages = [
            (self._calculate_importance(msg, messages), msg)
            for msg in messages
        ]
        
        # 按分数排序
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        # 选择最重要的消息，直到达到限制
        compressed = []
        tokens_used = 0
        
        for score, msg in scored_messages:
            tokens = self.tokenizer(msg.content)
            
            if max_tokens and tokens_used + tokens > max_tokens:
                continue
            
            if max_messages and len(compressed) >= max_messages:
                break
            
            compressed.append(msg)
            if max_tokens:
                tokens_used += tokens
        
        # 按时间顺序重新排序
        compressed.sort(key=lambda msg: msg.timestamp)
        
        return compressed
```

---

## 五、检索引擎设计（可插拔）

### 5.1 RetrievalEngine 接口

```python
class RetrievalEngine(ABC):
    """检索引擎接口"""
    
    @abstractmethod
    def search(
    self,
        messages: List[Message],
        query: str,
        top_k: int = 5
    ) -> List[Message]:
        """搜索相关消息"""
        pass
```

### 5.2 KeywordRetrievalEngine（关键词检索）

```python
class KeywordRetrievalEngine(RetrievalEngine):
    """关键词检索引擎"""
    
    def search(
        self,
        messages: List[Message],
        query: str,
        top_k: int = 5
    ) -> List[Message]:
        """搜索相关消息"""
        query_words = set(query.lower().split())
        scored_messages = []
        
        for msg in messages:
            content_words = set(msg.content.lower().split())
            score = len(query_words & content_words)
            if score > 0:
                scored_messages.append((score, msg))
        
        # 按分数排序
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        return [msg for _, msg in scored_messages[:top_k]]
```

---

## 六、ContextManager 统一接口

### 6.1 ContextManager 实现

```python
from typing import Optional, Dict, Any
import uuid

class ContextManager:
    """上下文管理器（统一接口）"""
    
    def __init__(
        self,
        storage_backend: Optional[StorageBackend] = None,
        compression_strategy: Optional[CompressionStrategy] = None,
        retrieval_engine: Optional[RetrievalEngine] = None,
        default_max_messages: int = 10,
        default_max_tokens: Optional[int] = None
    ):
        """
        初始化上下文管理器
        
        Args:
            storage_backend: 存储后端（默认：FileStorageBackend，持久化）
            compression_strategy: 压缩策略（默认：TimeWindowCompression）
            retrieval_engine: 检索引擎（默认：KeywordRetrievalEngine）
            long_term_memory: 长期记忆（可选）
            default_max_messages: 默认最大消息数
            default_max_tokens: 默认最大 token 数
        """
        # 默认使用 FileStorageBackend（持久化）
        self.storage = storage_backend or FileStorageBackend()
        self.compression = compression_strategy or TimeWindowCompression()
        self.retrieval = retrieval_engine or KeywordRetrievalEngine()
        self.default_max_messages = default_max_messages
        self.default_max_tokens = default_max_tokens
        # 长期记忆（可选）
        self.long_term_memory: Optional[LongTermMemory] = None
    
    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新会话
        
        Args:
            metadata: 会话元数据
            
        Returns:
            会话 ID
        """
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            metadata=metadata or {}
        )
        self.storage.create_session(session)
        return session_id
    
    def add_message(
    self,
    session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
) -> str:
        """
        添加消息
        
        Args:
            session_id: 会话 ID
            role: 消息角色
            content: 消息内容
            metadata: 消息元数据
            
        Returns:
            消息 ID
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.storage.save_message(session_id, message)
        return message.message_id
    
    def get_messages(
        self,
        session_id: str,
        max_messages: Optional[int] = None,
        max_tokens: Optional[int] = None,
        compressed: bool = True
    ) -> List[Message]:
        """
        获取消息列表
        
        Args:
            session_id: 会话 ID
            max_messages: 最大消息数（None 使用默认值）
            max_tokens: 最大 token 数（None 使用默认值）
            compressed: 是否应用压缩
            
        Returns:
            消息列表
        """
        messages = self.storage.get_messages(session_id)
        
        if not messages:
            return []
        
        # 应用压缩
        if compressed:
            max_msg = max_messages or self.default_max_messages
            max_tok = max_tokens or self.default_max_tokens
            messages = self.compression.compress(messages, max_tok, max_msg)
        
        return messages
    
    def get_messages_for_llm(
        self,
        session_id: str,
        max_messages: Optional[int] = None,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        获取用于 LLM 的消息格式
        
        Args:
            session_id: 会话 ID
            max_messages: 最大消息数
            max_tokens: 最大 token 数
            
        Returns:
            LLM 格式的消息列表
        """
        messages = self.get_messages(session_id, max_messages, max_tokens)
        return [
            {
                "role": msg.role.value,
                "content": msg.content
            }
            for msg in messages
        ]
    
    def search_messages(
        self,
        session_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Message]:
        """
        搜索相关消息
        
        Args:
            session_id: 会话 ID
            query: 搜索查询
            top_k: 返回前 K 条消息
            
        Returns:
            相关消息列表
        """
        messages = self.storage.get_messages(session_id)
        return self.retrieval.search(messages, query, top_k)
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        return self.storage.clear_session(session_id)
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.storage.get_session(session_id)
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        return self.storage.list_sessions(limit)
```

---

## 七、使用示例

### 7.1 基本使用

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
print(f"会话包含 {len(messages)} 条消息")

# 获取用于 LLM 的格式
llm_messages = context_manager.get_messages_for_llm(session_id)
```

### 7.2 使用文件存储

```python
from backend.core.context import ContextManager, FileStorageBackend
from pathlib import Path

# 创建文件存储后端
storage = FileStorageBackend(storage_dir=Path("data/contexts"))

# 创建上下文管理器
context_manager = ContextManager(storage_backend=storage)

# 使用方式与基本使用相同
session_id = context_manager.create_session()
context_manager.add_message(session_id, MessageRole.USER, "消息内容")
```

### 7.3 使用 Token 限制压缩

```python
from backend.core.context import (
    ContextManager,
    TokenLimitCompression,
    MessageRole
)

# 创建压缩策略
compression = TokenLimitCompression()

# 创建上下文管理器
context_manager = ContextManager(
    compression_strategy=compression,
    default_max_tokens=8000
)

# 添加消息
session_id = context_manager.create_session()
for i in range(100):
    context_manager.add_message(
        session_id,
        MessageRole.USER,
        f"消息 {i}: " + "x" * 1000  # 长消息
    )

# 获取消息（自动压缩到 8000 tokens）
messages = context_manager.get_messages(session_id)
print(f"压缩后消息数: {len(messages)}")
```

### 7.4 多 Agent 共享使用

```python
# Agent A 使用
agent_a_context = ContextManager(
    storage_backend=FileStorageBackend(Path("data/agent_a/contexts")),
    default_max_messages=20
)

# Agent B 使用
agent_b_context = ContextManager(
    storage_backend=FileStorageBackend(Path("data/agent_b/contexts")),
    compression_strategy=ImportanceScoringCompression(),
    default_max_tokens=16000
)

# 每个 Agent 独立管理自己的上下文
session_a = agent_a_context.create_session()
session_b = agent_b_context.create_session()
```

---

## 八、扩展性设计

### 8.1 自定义存储后端

```python
class RedisStorageBackend(StorageBackend):
    """Redis 存储后端（示例）"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def save_message(self, session_id: str, message: Message) -> bool:
        # 实现 Redis 存储逻辑
        pass
    
    # ... 实现其他方法
```

### 8.2 自定义压缩策略

```python
class LLMSummarizationCompression(CompressionStrategy):
    """使用 LLM 生成摘要的压缩策略"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
    
    def compress(self, messages, max_tokens=None, max_messages=None):
        # 使用 LLM 生成摘要
        # 保留重要消息，将旧消息压缩为摘要
        pass
```

### 8.3 自定义检索引擎

```python
class VectorRetrievalEngine(RetrievalEngine):
    """向量检索引擎"""
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
    
    def search(self, messages, query, top_k=5):
        # 使用向量相似度搜索
        pass
```

---

## 九、模块结构

```
backend/core/context/
├── __init__.py                 # 导出主要接口
├── manager.py                  # ContextManager 主类
├── models.py                   # Message, Session 数据模型
├── storage/
│   ├── __init__.py
│   ├── base.py                 # StorageBackend 接口
│   ├── memory.py               # MemoryStorageBackend
│   ├── file.py                 # FileStorageBackend（默认，持久化）
│   └── database.py             # DatabaseStorageBackend
├── compression/
│   ├── __init__.py
│   ├── base.py                 # CompressionStrategy 接口
│   ├── time_window.py          # TimeWindowCompression
│   ├── token_limit.py          # TokenLimitCompression
│   └── importance.py           # ImportanceScoringCompression
├── retrieval/
│   ├── __init__.py
│   ├── base.py                 # RetrievalEngine 接口
│   ├── keyword.py              # KeywordRetrievalEngine
│   └── vector.py                # VectorRetrievalEngine（可选）
└── long_term_memory/
    ├── __init__.py
    ├── base.py                 # LongTermMemory 接口
    ├── models.py               # Memory 数据模型
    ├── file.py                 # FileLongTermMemory（默认）
    └── vector.py               # VectorLongTermMemory（可选，语义搜索）
```

---

## 十、长期记忆模块设计

### 10.1 长期记忆概述

**长期记忆**用于跨会话保存和检索历史信息，与上下文管理（会话级）不同：

- **上下文管理**: 管理当前会话的对话历史（短期）
- **长期记忆**: 保存跨会话的知识、经验、重要信息（长期）

### 10.2 长期记忆架构

```
┌─────────────────────────────────────────────────────────┐
│              LongTermMemory (长期记忆)                    │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Memory Store  │  │ Vector Store │  │ Index Store  │  │
│  │ (持久化存储)   │  │ (语义搜索)    │  │ (索引管理)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 10.3 长期记忆数据模型

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class MemoryType(str, Enum):
    """记忆类型"""
    CONVERSATION = "conversation"  # 对话记忆
    KNOWLEDGE = "knowledge"        # 知识记忆
    PREFERENCE = "preference"      # 用户偏好
    CODE = "code"                  # 代码记忆
    TASK = "task"                  # 任务记忆

@dataclass
class Memory:
    """长期记忆数据模型"""
    memory_id: str
    memory_type: MemoryType
    content: str
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """从字典创建"""
        return cls(
            memory_id=data["memory_id"],
            memory_type=MemoryType(data["memory_type"]),
            content=data["content"],
            summary=data.get("summary"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None
        )
```

### 10.4 LongTermMemory 接口

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class LongTermMemory(ABC):
    """长期记忆接口"""
    
    @abstractmethod
    def save_memory(self, memory: Memory) -> bool:
        """保存记忆"""
        pass
    
    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        pass
    
    @abstractmethod
    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 10
    ) -> List[Memory]:
        """搜索记忆"""
        pass
    
    @abstractmethod
    def get_memories_by_tags(
        self,
        tags: List[str],
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """根据标签获取记忆"""
        pass
    
    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def update_memory(self, memory: Memory) -> bool:
        """更新记忆"""
        pass
```

### 10.5 FileLongTermMemory 实现

```python
import json
from pathlib import Path
from typing import List, Optional
import uuid

class FileLongTermMemory(LongTermMemory):
    """基于文件的长期记忆实现"""
    
    def __init__(self, storage_dir: Path = Path("data/long_term_memory")):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memories_dir = self.storage_dir / "memories"
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.index = {
                    memory_id: Memory.from_dict(m)
                    for memory_id, m in data.get("memories", {}).items()
                }
        else:
            self.index = {}
    
    def _save_index(self):
        """保存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump({
                "memories": {
                    memory_id: memory.to_dict()
                    for memory_id, memory in self.index.items()
                }
            }, f, ensure_ascii=False, indent=2)
    
    def _get_memory_file(self, memory_id: str) -> Path:
        """获取记忆文件路径"""
        return self.memories_dir / f"{memory_id}.json"
    
    def save_memory(self, memory: Memory) -> bool:
        """保存记忆"""
        if not memory.memory_id:
            memory.memory_id = str(uuid.uuid4())
        
        # 保存到文件
        memory_file = self._get_memory_file(memory.memory_id)
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新索引
        self.index[memory.memory_id] = memory
        self._save_index()
        
        return True
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        if memory_id in self.index:
            memory_file = self._get_memory_file(memory_id)
            if memory_file.exists():
                with open(memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    memory = Memory.from_dict(data)
                    # 更新访问信息
                    memory.access_count += 1
                    memory.last_accessed = datetime.now()
                    self.save_memory(memory)
                    return memory
        return None
    
    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 10
    ) -> List[Memory]:
        """搜索记忆（简单关键词匹配）"""
        query_words = set(query.lower().split())
        scored_memories = []
        
        for memory in self.index.values():
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # 关键词匹配
            content_words = set(memory.content.lower().split())
            summary_words = set((memory.summary or "").lower().split())
            tag_words = set([tag.lower() for tag in memory.tags])
            
            score = (
                len(query_words & content_words) * 3 +
                len(query_words & summary_words) * 2 +
                len(query_words & tag_words)
            )
            
            if score > 0:
                scored_memories.append((score, memory))
        
        # 按分数排序
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        return [memory for _, memory in scored_memories[:top_k]]
    
    def get_memories_by_tags(
        self,
        tags: List[str],
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """根据标签获取记忆"""
        tag_set = set([tag.lower() for tag in tags])
        memories = []
        
        for memory in self.index.values():
            if memory_type and memory.memory_type != memory_type:
                continue
            
            memory_tags = set([tag.lower() for tag in memory.tags])
            if tag_set & memory_tags:
                memories.append(memory)
        
        return memories
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self.index:
            memory_file = self._get_memory_file(memory_id)
            if memory_file.exists():
                memory_file.unlink()
            
            del self.index[memory_id]
            self._save_index()
            return True
        
        return False
    
    def update_memory(self, memory: Memory) -> bool:
        """更新记忆"""
        if memory.memory_id in self.index:
            memory.updated_at = datetime.now()
            return self.save_memory(memory)
        return False
```

### 10.6 ContextManager 与长期记忆集成

```python
class ContextManager:
    """上下文管理器（统一接口）"""
    
    def __init__(
        self,
        storage_backend: Optional[StorageBackend] = None,
        compression_strategy: Optional[CompressionStrategy] = None,
        retrieval_engine: Optional[RetrievalEngine] = None,
        long_term_memory: Optional[LongTermMemory] = None,
        default_max_messages: int = 10,
        default_max_tokens: Optional[int] = None,
        auto_save_to_memory: bool = False  # 是否自动保存到长期记忆
    ):
        # 默认使用 FileStorageBackend（持久化）
        self.storage = storage_backend or FileStorageBackend()
        self.compression = compression_strategy or TimeWindowCompression()
        self.retrieval = retrieval_engine or KeywordRetrievalEngine()
        self.long_term_memory = long_term_memory
        self.auto_save_to_memory = auto_save_to_memory
        self.default_max_messages = default_max_messages
        self.default_max_tokens = default_max_tokens
    
    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        save_to_memory: Optional[bool] = None  # None 使用 auto_save_to_memory
    ) -> str:
        """添加消息"""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        # 保存到上下文
        self.storage.save_message(session_id, message)
        
        # 可选：保存到长期记忆
        should_save = save_to_memory if save_to_memory is not None else self.auto_save_to_memory
        if should_save and self.long_term_memory and role == MessageRole.USER:
            # 保存用户消息到长期记忆
            memory = Memory(
                memory_id=str(uuid.uuid4()),
                memory_type=MemoryType.CONVERSATION,
                content=content,
                metadata={
                    "session_id": session_id,
                    "role": role.value,
                    **metadata or {}
                }
            )
            self.long_term_memory.save_memory(memory)
        
        return message.message_id
    
    def get_relevant_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 5
    ) -> List[Memory]:
        """从长期记忆获取相关信息"""
        if not self.long_term_memory:
            return []
        
        return self.long_term_memory.search_memories(query, memory_type, top_k)
```

### 10.7 使用示例

```python
from backend.core.context import (
    ContextManager,
    FileStorageBackend,
    FileLongTermMemory,
    MemoryType
)

# 创建长期记忆
long_term_memory = FileLongTermMemory(Path("data/long_term_memory"))

# 创建上下文管理器（带长期记忆）
context_manager = ContextManager(
    storage_backend=FileStorageBackend(Path("data/contexts")),
    long_term_memory=long_term_memory,
    auto_save_to_memory=True  # 自动保存到长期记忆
)

# 创建会话
session_id = context_manager.create_session()

# 添加消息（自动保存到长期记忆）
context_manager.add_message(session_id, MessageRole.USER, "我喜欢使用 Python")

# 从长期记忆检索相关信息
memories = context_manager.get_relevant_memories("Python", top_k=5)
for memory in memories:
    print(f"相关记忆: {memory.content}")
```

---

## 十一、实现优先级

### 阶段 1: 核心功能（P0）
- ✅ Message 和 Session 数据模型
- ✅ StorageBackend 接口
- ✅ **FileStorageBackend（持久化，默认）** ⭐
- ✅ CompressionStrategy 接口和 TimeWindowCompression
- ✅ ContextManager 统一接口
- ✅ 基本使用示例

### 阶段 2: 长期记忆基础（P0）⭐
- ⏳ Memory 数据模型
- ⏳ LongTermMemory 接口
- ⏳ FileLongTermMemory 实现（Memory Store + Index Store，无向量存储）
- ⏳ ContextManager 与长期记忆集成
- ⏳ 长期记忆使用示例（关键词搜索）

**注意**: 长期记忆的详细实现优先级请参考：
- `docs/design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md`

### 阶段 3: 持久化存储（P1）
- ⏳ DatabaseStorageBackend
- ⏳ 存储后端切换测试

### 阶段 4: 高级压缩（P1）
- ⏳ TokenLimitCompression
- ⏳ ImportanceScoringCompression
- ⏳ 压缩策略性能测试

### 阶段 5: 检索功能和语义搜索（P1）
- ⏳ KeywordRetrievalEngine
- ⏳ 检索功能测试
- ⏳ **长期记忆语义搜索（Vector Store: Chroma）**
- ⏳ 向量嵌入生成（需要 embedding 模型）
- ⏳ 语义搜索集成

### 阶段 6: 扩展功能（P3）
- ⏳ VectorRetrievalEngine
- ⏳ LLMSummarizationCompression
- ⏳ RedisStorageBackend（如需要）

---

## 十二、技术选型

### 11.1 存储后端技术栈

| 存储类型 | 技术栈 | 依赖 | 适用场景 |
|---------|--------|------|---------|
| **Memory** | `collections.deque` + `dict` | 无 | 临时存储、开发测试 |
| **File** | `json` (标准库) | 无 | 单机持久化、中小规模 |
| **Database** | `sqlite3` (标准库) | 无 | 需要查询、事务支持 |

**核心原则**: 所有默认实现使用 Python 标准库，零依赖 ✅

**未来扩展**:
- File: 可扩展 MessagePack（需要 `msgpack` 库）
- Database: 可扩展 PostgreSQL（需要 `psycopg2`）或 Redis（需要 `redis` 库）

详细技术选型分析请参考：`docs/design/01-context-storage-and-compression-design-technology-selection.md`

## 十三、长期记忆技术选型

### 12.1 技术选型总结

| 组件 | 推荐技术 | 依赖 | 适用场景 |
|------|---------|------|---------|
| **Memory Store** | `json` (标准库) | 无 | 中小规模，需要可读性 |
| **Vector Store** | `chromadb` | 需要 | 语义搜索，中小规模 |
| **Index Store** | `json` (标准库) | 无 | 中小规模，需要可读性 |

### 12.2 核心依赖

**必需依赖**:
- `chromadb`: 向量存储和语义搜索（用于语义搜索功能）

**可选依赖**（未来扩展）:
- `faiss-cpu`: 如果向量数据量超大
- `qdrant-client`: 如果需要生产环境部署

详细技术选型分析请参考：`docs/design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md`

## 十四、相关文档

- `docs/design/01-code-and-memory-design.md` - 代码和记忆设计
- `docs/design/00-architecture-design.md` - 架构设计
- `docs/design/01-context-storage-and-compression-design-technology-selection.md` - 上下文存储技术选型
- `docs/design/01-context-storage-and-compression-design-long-term-memory-technology-selection.md` - 长期记忆技术选型
- `backend/core/agent/context_manager.py` - 当前实现（将被替换）

---

**创建时间**: 2025-01-01  
**最后更新**: 2025-01-01  
**版本**: 2.0  
**状态**: 设计完成，待实现
