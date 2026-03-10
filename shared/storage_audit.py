"""存储审计：收集项目所用存储、临时文件、输出、数据库、配置等"""
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.platform_utils import (
    get_app_data_dir,
    get_default_output_dir,
    get_temp_root_dir,
)
from shared.storage_utils import get_storage_manager

logger = logging.getLogger(__name__)

# 有输出目录的任务类型（与 task_handlers 的 output_spec.default_path 对应）
TASK_TYPES_WITH_OUTPUT = [
    "video_download",
    "speech_to_text",
    "video_extract_audio",
    "image_generation",
]

# 已知的数据库文件名（非临时），用于分组展示
KNOWN_DB_NAMES = frozenset({
    "task_queue.db",
    "llm_audit.db",
    "article_revisions.db",
    "sessions.db",
    "contexts.db",
    "test_results.db",
})


def _is_tmp_db(name: str) -> bool:
    """判断是否为临时数据库（可安全清理）"""
    return name.startswith("tmp") and name.endswith(".db") and name != "tmp.db"


def _dir_size_bytes(path: Path, max_depth: int = 10) -> int:
    """递归计算目录大小（字节），权限错误时返回 0"""
    if not path.exists() or not path.is_dir():
        return 0
    total = 0
    try:
        for p in path.rglob("*"):
            if max_depth >= 0 and len(p.relative_to(path).parts) > max_depth:
                continue
            try:
                if p.is_file():
                    total += p.stat().st_size
            except (OSError, PermissionError) as e:
                logger.debug("跳过文件 %s: %s", p, e)
    except (OSError, PermissionError) as e:
        logger.debug("计算目录大小失败 %s: %s", path, e)
    return total


def _file_size(path: Path) -> int:
    """获取文件大小，不存在或非文件返回 0"""
    try:
        if path.exists() and path.is_file():
            return path.stat().st_size
    except (OSError, PermissionError):
        pass
    return 0


def _format_size(size_bytes: int) -> Dict[str, Any]:
    """将字节数格式化为可读形式"""
    if size_bytes < 1024:
        return {"bytes": size_bytes, "human": f"{size_bytes} B"}
    if size_bytes < 1024 * 1024:
        return {"bytes": size_bytes, "human": f"{size_bytes / 1024:.2f} KB"}
    if size_bytes < 1024 * 1024 * 1024:
        return {"bytes": size_bytes, "human": f"{size_bytes / (1024 * 1024):.2f} MB"}
    return {"bytes": size_bytes, "human": f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"}


def collect_storage_audit(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    收集存储审计数据：应用数据、临时文件、输出、数据库、配置、系统临时目录等。

    Args:
        project_root: 项目根目录，用于定位 .env 等；None 时尝试从 __file__ 推断

    Returns:
        审计结果字典，含 success、error（失败时）、audit（成功时）
    """
    if project_root is None:
        # shared/storage_audit.py -> 项目根
        project_root = Path(__file__).resolve().parent.parent

    try:
        storage_manager = get_storage_manager()
        app_data = get_app_data_dir()
        temp_root = get_temp_root_dir()
        default_output = get_default_output_dir()

        # 1. 应用数据目录（含 databases、chroma、tmp 等）
        app_data_size = _dir_size_bytes(app_data)
        app_data_subdirs: List[Dict[str, Any]] = []
        for sub in ["databases", "chroma", "tmp", "contexts"]:
            p = app_data / sub
            if p.exists():
                sz = _dir_size_bytes(p)
                app_data_subdirs.append({
                    "name": sub,
                    "path": str(p),
                    "size_bytes": sz,
                    **(_format_size(sz)),
                })

        # 2. 临时文件根目录（项目统一 tmp）
        temp_root_size = _dir_size_bytes(temp_root)

        # 3. 系统临时目录中的 hou-cli 相关子目录
        system_temp = Path(tempfile.gettempdir())
        system_temp_items: List[Dict[str, Any]] = []
        for name in ["hou-cli-sandbox", "hou-cli-pdf"]:
            p = system_temp / name
            if p.exists():
                sz = _dir_size_bytes(p)
                system_temp_items.append({
                    "name": name,
                    "path": str(p),
                    "size_bytes": sz,
                    **(_format_size(sz)),
                })

        # 4. 输出目录（~/hou-cli/outputs 及按任务类型子目录）
        output_root = default_output
        output_root_size = _dir_size_bytes(output_root)
        output_subdirs: List[Dict[str, Any]] = []
        for task_type in TASK_TYPES_WITH_OUTPUT:
            p = output_root / task_type
            if p.exists():
                sz = _dir_size_bytes(p)
                output_subdirs.append({
                    "task_type": task_type,
                    "path": str(p),
                    "size_bytes": sz,
                    **(_format_size(sz)),
                })

        # 5. 数据库文件（分组：已知 vs 临时）
        db_dir = storage_manager.get_db_dir()
        known_dbs: List[Dict[str, Any]] = []
        tmp_dbs: List[Dict[str, Any]] = []
        if db_dir.exists():
            for db_file in db_dir.glob("*.db"):
                try:
                    sz = db_file.stat().st_size
                    entry = {
                        "name": db_file.name,
                        "path": str(db_file),
                        "size_bytes": sz,
                        **(_format_size(sz)),
                    }
                    if _is_tmp_db(db_file.name):
                        tmp_dbs.append(entry)
                    else:
                        known_dbs.append(entry)
                except (OSError, PermissionError):
                    pass

        # 6. 配置数据（.env、port.txt 等）
        config_files: List[Dict[str, Any]] = []
        env_path = project_root / ".env"
        if env_path.exists():
            sz = _file_size(env_path)
            config_files.append({
                "name": ".env",
                "path": str(env_path),
                "size_bytes": sz,
                **(_format_size(sz)),
            })
        port_file = app_data / "port.txt"
        if port_file.exists():
            sz = _file_size(port_file)
            config_files.append({
                "name": "port.txt",
                "path": str(port_file),
                "size_bytes": sz,
                **(_format_size(sz)),
            })

        # 7. ChromaDB
        chroma_dir = storage_manager.get_chroma_dir()
        chroma_size = _dir_size_bytes(chroma_dir)
        chroma_collections: List[Dict[str, Any]] = []
        try:
            client = storage_manager.get_chroma_client()
            for col in client.list_collections():
                count = col.count() if hasattr(col, "count") else 0
                chroma_collections.append({
                    "name": col.name,
                    "count": count,
                    "metadata": col.metadata if hasattr(col, "metadata") else {},
                })
        except Exception as e:
            logger.debug("ChromaDB 集合列表失败: %s", e)

        # 8. 会话/上下文存储（contexts.db 在 databases 中，file 模式可能有 sessions 目录）
        # contexts 使用 DatabaseStorageBackend 时在 app_data/databases/contexts.db
        # 若使用 FileStorageBackend，可能在 app_data 下某目录
        # 此处 databases 已覆盖，不重复

        # 汇总
        total_bytes = (
            app_data_size
            + temp_root_size
            + output_root_size
            + sum(d["size_bytes"] for d in system_temp_items)
        )

        return {
            "success": True,
            "audit": {
                "summary": {
                    "total_bytes": total_bytes,
                    **_format_size(total_bytes),
                },
                "app_data": {
                    "path": str(app_data),
                    "size_bytes": app_data_size,
                    **_format_size(app_data_size),
                    "subdirs": app_data_subdirs,
                },
                "temp_root": {
                    "path": str(temp_root),
                    "size_bytes": temp_root_size,
                    **_format_size(temp_root_size),
                },
                "system_temp": {
                    "base_path": str(system_temp),
                    "items": system_temp_items,
                },
                "outputs": {
                    "path": str(output_root),
                    "size_bytes": output_root_size,
                    **_format_size(output_root_size),
                    "subdirs": output_subdirs,
                },
                "databases": {
                    "dir": str(db_dir),
                    "known": known_dbs,
                    "tmp": tmp_dbs,
                    "known_total_bytes": sum(d["size_bytes"] for d in known_dbs),
                    "tmp_total_bytes": sum(d["size_bytes"] for d in tmp_dbs),
                    "tmp_count": len(tmp_dbs),
                },
                "config": {
                    "files": config_files,
                },
                "chromadb": {
                    "path": str(chroma_dir),
                    "size_bytes": chroma_size,
                    **_format_size(chroma_size),
                    "collections": chroma_collections,
                },
            },
        }
    except Exception as e:
        logger.exception("存储审计失败")
        return {"success": False, "error": str(e)}


def cleanup_tmp_databases() -> Dict[str, Any]:
    """
    清理 databases 目录下的 tmp*.db 临时文件。
    仅删除符合 _is_tmp_db 规则的文件。

    Returns:
        {"success": True, "deleted_count": N, "freed_bytes": M} 或 {"success": False, "error": "..."}
    """
    try:
        storage_manager = get_storage_manager()
        db_dir = storage_manager.get_db_dir()
        if not db_dir.exists():
            return {"success": True, "deleted_count": 0, "freed_bytes": 0}
        deleted = 0
        freed = 0
        for db_file in db_dir.glob("*.db"):
            if not _is_tmp_db(db_file.name):
                continue
            try:
                sz = db_file.stat().st_size
                db_file.unlink()
                deleted += 1
                freed += sz
            except (OSError, PermissionError) as e:
                logger.warning("删除临时数据库失败 %s: %s", db_file, e)
        return {"success": True, "deleted_count": deleted, "freed_bytes": freed}
    except Exception as e:
        logger.exception("清理临时数据库失败")
        return {"success": False, "error": str(e)}
