"""存储配置相关路由"""

from fastapi import APIRouter

from shared.debug_utils import debug_log
from shared.storage_utils import get_storage_manager
from shared.platform_utils import get_default_output_dir, get_temp_root_dir
from shared.storage_audit import collect_storage_audit, cleanup_tmp_databases


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
        
        # 获取 SQLite 数据库文件列表（分组：已知 vs 临时）
        from shared.storage_audit import _is_tmp_db
        sqlite_files = []
        known_databases: list = []
        tmp_databases: list = []
        if db_dir.exists():
            for db_file in db_dir.glob("*.db"):
                try:
                    size = db_file.stat().st_size
                    entry = {
                        "name": db_file.name,
                        "path": str(db_file),
                        "size": size,
                        "size_mb": round(size / (1024 * 1024), 2)
                    }
                    sqlite_files.append(entry)
                    if _is_tmp_db(db_file.name):
                        tmp_databases.append(entry)
                    else:
                        known_databases.append(entry)
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
        
        # 获取数据目录信息（应用数据目录）
        data_dir = storage_manager.get_data_dir()
        # 项目统一输出目录与临时目录（跨功能统一使用）
        default_output_dir = get_default_output_dir()
        temp_root_dir = get_temp_root_dir()
        # LLM 审计使用独立 SQLite 库
        try:
            from backend.services.llm.llm_audit import get_audit_dir
            audit_path = get_audit_dir()
            llm_audit_db_path = str(audit_path) if audit_path else None
        except Exception:
            llm_audit_db_path = None
        # Tavily API 调用审计
        try:
            from backend.services.tavily_search_service.tavily_usage_audit import get_tavily_audit_path
            tavily_audit_db_path = get_tavily_audit_path()
        except Exception:
            tavily_audit_db_path = None

        return {
            "success": True,
            # 核心路径：项目数据目录 / 默认输出目录 / 临时目录
            "paths": {
                "data_dir": str(data_dir),
                "default_output_dir": str(default_output_dir),
                "temp_root_dir": str(temp_root_dir),
            },
            # 兼容旧字段，仍保留 data_dir 顶层字段
            "data_dir": str(data_dir),
            "llm_audit_db_path": llm_audit_db_path,
            "tavily_audit_db_path": tavily_audit_db_path,
            "sqlite": {
                "enabled": True,
                "db_dir": str(db_dir),
                "default_db_path": str(sqlite_path),
                "default_db_exists": sqlite_exists,
                "default_db_size": sqlite_size,
                "default_db_size_mb": round(sqlite_size / (1024 * 1024), 2) if sqlite_size > 0 else 0,
                "databases": sqlite_files,
                "known_databases": known_databases,
                "tmp_databases": tmp_databases,
                "tmp_count": len(tmp_databases),
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


@router.get("/storage/audit")
async def get_storage_audit():
    """获取存储审计：应用数据、临时文件、输出、数据库、配置、系统临时目录等"""
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent
    result = collect_storage_audit(project_root)
    if result.get("success"):
        return {"success": True, **result["audit"]}
    return {"success": False, "error": result.get("error", "未知错误")}


@router.post("/storage/audit/cleanup-tmp-dbs")
async def post_cleanup_tmp_databases():
    """清理 databases 目录下的 tmp*.db 临时文件（测试残留等）"""
    result = cleanup_tmp_databases()
    if result.get("success"):
        return {
            "success": True,
            "deleted_count": result.get("deleted_count", 0),
            "freed_bytes": result.get("freed_bytes", 0),
            "freed_human": f"{result.get('freed_bytes', 0) / (1024 * 1024):.2f} MB"}
    return {"success": False, "error": result.get("error", "未知错误")}
