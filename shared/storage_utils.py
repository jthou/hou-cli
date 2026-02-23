"""存储工具函数"""
from pathlib import Path
from typing import Optional
import sqlite3
import chromadb
from shared.platform_utils import get_app_data_dir


class StorageManager:
    """统一存储管理器"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化存储管理器
        
        Args:
            data_dir: 数据目录，如果为 None 则使用默认应用数据目录
        """
        self.data_dir = data_dir or get_app_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite 数据库目录
        self.db_dir = self.data_dir / "databases"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # ChromaDB 数据目录
        self.chroma_dir = self.data_dir / "chroma"
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 ChromaDB 客户端
        self._chroma_client = None
    
    def get_sqlite_path(self, db_name: str = "sessions.db") -> Path:
        """获取 SQLite 数据库文件路径"""
        return self.db_dir / db_name
    
    def get_sqlite_connection(
        self,
        db_name: str = "sessions.db",
        enable_wal: bool = True
    ) -> sqlite3.Connection:
        """
        获取 SQLite 连接
        
        Args:
            db_name: 数据库文件名
            enable_wal: 是否启用 WAL 模式（推荐）
        
        Returns:
            SQLite 连接对象
        """
        db_path = self.get_sqlite_path(db_name)
        conn = sqlite3.connect(str(db_path))
        
        if enable_wal:
            # 启用 WAL 模式（提高并发性能）
            conn.execute("PRAGMA journal_mode=WAL")
            # 设置同步模式（平衡性能和安全性）
            conn.execute("PRAGMA synchronous=NORMAL")
            # 设置缓存大小（64MB）
            conn.execute("PRAGMA cache_size=-64000")
        
        return conn
    
    def get_chroma_client(self) -> chromadb.PersistentClient:
        """获取 ChromaDB 持久化客户端"""
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(
                path=str(self.chroma_dir)
            )
        return self._chroma_client
    
    def get_chroma_collection(
        self,
        collection_name: str = "knowledge_base",
        metadata: Optional[dict] = None
    ) -> chromadb.Collection:
        """
        获取 ChromaDB 集合
        
        Args:
            collection_name: 集合名称
            metadata: 集合元数据
        
        Returns:
            ChromaDB 集合对象
        """
        client = self.get_chroma_client()
        return client.get_or_create_collection(
            name=collection_name,
            metadata=metadata or {}
        )
    
    def get_data_dir(self) -> Path:
        """获取数据目录"""
        return self.data_dir
    
    def get_db_dir(self) -> Path:
        """获取数据库目录"""
        return self.db_dir
    
    def get_chroma_dir(self) -> Path:
        """获取 ChromaDB 目录"""
        return self.chroma_dir


# 全局存储管理器实例（单例模式）
_storage_manager: Optional[StorageManager] = None


def get_storage_manager(data_dir: Optional[Path] = None) -> StorageManager:
    """
    获取全局存储管理器实例
    
    Args:
        data_dir: 数据目录，如果为 None 则使用默认应用数据目录
    
    Returns:
        存储管理器实例
    """
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager(data_dir)
    return _storage_manager
