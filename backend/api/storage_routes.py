"""存储配置相关路由"""
from pathlib import Path
from fastapi import APIRouter
from shared.debug_utils import debug_log
from shared.storage_utils import get_storage_manager

router = APIRouter()

@router.get("/storage/config")
async def get_storage_config():
    """获取存储配置信息（SQLite 和 ChromaDB）
    
    Returns:
        存储配置信息，包括路径、状态等
    """
    try:
        storage_manager = get_storage_manager()
        
        # 获取 SQLite 信息
        sqlite_path = storage_manager.get_sqlite_path()
        db_dir = storage_manager.get_db_dir()
        
        # 检查 SQLite 数据库文件是否存在
        sqlite_exists = sqlite_path.exists()
        sqlite_size = sqlite_path.stat().st_size if sqlite_exists else 0
        
        # 获取 SQLite 数据库文件列表
        sqlite_files = []
        if db_dir.exists():
            for db_file in db_dir.glob("*.db"):
                try:
                    size = db_file.stat().st_size
                    sqlite_files.append({
                        "name": db_file.name,
                        "path": str(db_file),
                        "size": size,
                        "size_mb": round(size / (1024 * 1024), 2)
                    })
                except Exception:
                    pass
        
        # 获取 ChromaDB 信息
        chroma_dir = storage_manager.get_chroma_dir()
        chroma_exists = chroma_dir.exists()
        
        # 计算 ChromaDB 目录大小
        chroma_size = 0
        chroma_collections = []
        if chroma_exists:
            try:
                # 计算目录大小
                for path in chroma_dir.rglob("*"):
                    if path.is_file():
                        chroma_size += path.stat().st_size
                
                # 获取 ChromaDB 集合列表
                try:
                    chroma_client = storage_manager.get_chroma_client()
                    collections = chroma_client.list_collections()
                    chroma_collections = [
                        {
                            "name": col.name,
                            "count": col.count() if hasattr(col, 'count') else 0,
                            "metadata": col.metadata if hasattr(col, 'metadata') else {}
                        }
                        for col in collections
                    ]
                except Exception as e:
                    debug_log(f"Failed to get ChromaDB collections: {str(e)}", level="warning")
            except Exception as e:
                debug_log(f"Failed to calculate ChromaDB size: {str(e)}", level="warning")
        
        # 获取数据目录信息
        data_dir = storage_manager.get_data_dir()
        
        return {
            "success": True,
            "data_dir": str(data_dir),
            "sqlite": {
                "enabled": True,
                "db_dir": str(db_dir),
                "default_db_path": str(sqlite_path),
                "default_db_exists": sqlite_exists,
                "default_db_size": sqlite_size,
                "default_db_size_mb": round(sqlite_size / (1024 * 1024), 2) if sqlite_size > 0 else 0,
                "databases": sqlite_files
            },
            "chromadb": {
                "enabled": True,
                "data_dir": str(chroma_dir),
                "exists": chroma_exists,
                "size": chroma_size,
                "size_mb": round(chroma_size / (1024 * 1024), 2) if chroma_size > 0 else 0,
                "collections": chroma_collections,
                "collection_count": len(chroma_collections)
            }
        }
    except Exception as e:
        debug_log(
            f"获取存储配置失败: {str(e)}",
            level="error"
        )
        return {
            "success": False,
            "error": str(e)
        }

