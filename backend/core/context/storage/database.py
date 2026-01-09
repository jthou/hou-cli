"""数据库存储后端（SQLite）"""
import sqlite3
import json
import uuid
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from backend.core.context.models import Message, MessageRole, Session
from backend.core.context.storage.base import StorageBackend


class DatabaseStorageBackend(StorageBackend):
    """数据库存储后端（SQLite）"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库存储后端
        
        Args:
            db_path: 数据库文件路径，如果为 None，使用项目配置目录下的 contexts.db
        """
        if db_path is None:
            from shared.platform_utils import get_app_data_dir
            db_path = str(get_app_data_dir() / "contexts.db")
        self.db_path = db_path
        # 确保目录存在
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
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
        finally:
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
        
        try:
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
        finally:
            conn.close()
    
    def delete_message(self, session_id: str, message_id: str) -> bool:
        """删除消息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            return deleted
        finally:
            conn.close()
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def create_session(self, session: Session) -> bool:
        """创建会话"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
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
            return True
        finally:
            conn.close()
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT session_id, created_at, updated_at, metadata
                FROM sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            
            if row:
                return Session(
                    session_id=row[0],
                    created_at=datetime.fromisoformat(row[1]),
                    updated_at=datetime.fromisoformat(row[2]),
                    metadata=json.loads(row[3] if row[3] else "{}")
                )
            
            return None
        finally:
            conn.close()
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """列出会话"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT session_id, created_at, updated_at, metadata 
                FROM sessions 
                ORDER BY updated_at DESC
            """
            params = []
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            sessions = []
            for row in rows:
                sessions.append(Session(
                    session_id=row[0],
                    created_at=datetime.fromisoformat(row[1]),
                    updated_at=datetime.fromisoformat(row[2]),
                    metadata=json.loads(row[3] if row[3] else "{}")
                ))
            
            return sessions
        finally:
            conn.close()

