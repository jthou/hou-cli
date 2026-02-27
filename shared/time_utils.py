"""时间工具：后端统一使用 UTC"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """当前 UTC 时间（带时区信息）"""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """当前 UTC 时间，ISO 8601 格式（含 +00:00），前端可正确解析并转为本地显示"""
    return utc_now().isoformat()
