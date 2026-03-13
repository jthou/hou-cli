"""
Tavily API 调用审计：记录每次搜索的 query、credits_used、ts 等。
每月 1000 次免费额度，调用次数纳入审计。
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_NAME = "tavily_audit.db"
TABLE_NAME = "tavily_audit"


def _is_audit_disabled() -> bool:
    """环境变量 TAVILY_AUDIT_DISABLED=1|true|yes 时关闭审计写入。"""
    v = os.environ.get("TAVILY_AUDIT_DISABLED", "").strip().lower()
    return v in ("1", "true", "yes")


def _get_conn():
    """获取 tavily_audit 数据库连接并确保表存在。失败返回 None。"""
    try:
        from shared.storage_utils import get_storage_manager

        conn = get_storage_manager().get_sqlite_connection(DB_NAME)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tavily_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                query TEXT NOT NULL,
                credits_used INTEGER NOT NULL DEFAULT 1,
                search_depth TEXT NOT NULL DEFAULT 'basic',
                num_results INTEGER,
                response_time REAL,
                record TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tavily_audit_ts ON tavily_audit(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tavily_audit_query ON tavily_audit(query)")
        conn.commit()
        return conn
    except Exception as e:
        logger.warning("Tavily 审计数据库不可用: %s", e)
        return None


def get_tavily_audit_path() -> Optional[str]:
    """返回审计数据库文件路径，供 API 展示。不可用时为 None。"""
    try:
        from shared.storage_utils import get_storage_manager

        return str(get_storage_manager().get_sqlite_path(DB_NAME))
    except Exception:
        return None


def append_tavily_audit(
    query: str,
    credits_used: int = 1,
    search_depth: str = "basic",
    num_results: Optional[int] = None,
    response_time: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    追加一条 Tavily 调用审计记录。
    TAVILY_AUDIT_DISABLED=1 时不写入。

    Args:
        query: 搜索查询
        credits_used: 消耗的 API 额度（basic=1, advanced=2）
        search_depth: 搜索深度
        num_results: 返回结果数
        response_time: 响应耗时（秒）
        extra: 额外字段
    """
    if _is_audit_disabled():
        return
    conn = _get_conn()
    if conn is None:
        return
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = json.dumps(extra or {}, ensure_ascii=False) if extra else None
    try:
        conn.execute(
            """
            INSERT INTO tavily_audit (ts, query, credits_used, search_depth, num_results, response_time, record)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, query, credits_used, search_depth, num_results, response_time, record),
        )
        conn.commit()
    except Exception as e:
        logger.warning("写入 Tavily 审计日志失败: %s", e)
    finally:
        conn.close()


def get_tavily_usage_stats(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取 Tavily 调用统计（用于审计展示）。

    Returns:
        {
            "total_calls": int,
            "total_credits": int,
            "by_date": [{date, calls, credits}, ...],
            "from_date": str,
            "to_date": str,
        }
    """
    conn = _get_conn()
    if conn is None:
        return {"total_calls": 0, "total_credits": 0, "by_date": [], "from_date": None, "to_date": None}
    try:
        date_filter = ""
        params: List[Any] = []
        if from_date and to_date:
            date_filter = "WHERE substr(ts, 1, 10) BETWEEN ? AND ?"
            params = [from_date, to_date]
        elif from_date:
            date_filter = "WHERE substr(ts, 1, 10) >= ?"
            params = [from_date]
        elif to_date:
            date_filter = "WHERE substr(ts, 1, 10) <= ?"
            params = [to_date]

        cur = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM(credits_used), 0) FROM tavily_audit {date_filter}",
            params,
        )
        row = cur.fetchone()
        total_calls = row[0] or 0
        total_credits = int(row[1] or 0)

        cur = conn.execute(
            f"""
            SELECT substr(ts, 1, 10) AS d, COUNT(*), COALESCE(SUM(credits_used), 0)
            FROM tavily_audit {date_filter}
            GROUP BY d ORDER BY d DESC
            """,
            params,
        )
        by_date = [
            {"date": r[0], "calls": r[1], "credits": int(r[2])}
            for r in cur.fetchall()
        ]

        return {
            "total_calls": total_calls,
            "total_credits": total_credits,
            "by_date": by_date,
            "from_date": from_date,
            "to_date": to_date,
        }
    except Exception as e:
        logger.warning("读取 Tavily 审计统计失败: %s", e)
        return {"total_calls": 0, "total_credits": 0, "by_date": [], "from_date": None, "to_date": None}
    finally:
        conn.close()
