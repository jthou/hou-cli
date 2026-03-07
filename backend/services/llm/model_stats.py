"""
模型使用统计：响应时间、接受次数，供模型审计页展示与排名。
- 响应时间：从 llm_audit 中按 audit_id 配对 request/response，计算 duration_ms
- 接受次数：用户点击「接受修改」时写入 model_acceptance 表
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_NAME = "llm_audit.db"
ACCEPTANCE_TABLE = "model_acceptance"


def _get_conn():
    """复用 llm_audit 的数据库连接"""
    try:
        from shared.storage_utils import get_storage_manager
        conn = get_storage_manager().get_sqlite_connection(DB_NAME)
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ACCEPTANCE_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                model TEXT NOT NULL,
                session_id TEXT
            )
            """
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{ACCEPTANCE_TABLE}_model ON {ACCEPTANCE_TABLE}(model)")
        conn.commit()
        return conn
    except Exception as e:
        logger.warning("model_stats 数据库不可用: %s", e)
        return None


def record_acceptance(model: str, session_id: Optional[str] = None) -> None:
    """记录一次「接受修改」：用户采纳了该模型的输出"""
    conn = _get_conn()
    if conn is None:
        return
    ts = datetime.utcnow().isoformat() + "Z"
    try:
        conn.execute(
            f"INSERT INTO {ACCEPTANCE_TABLE} (ts, model, session_id) VALUES (?, ?, ?)",
            (ts, model, session_id or ""),
        )
        conn.commit()
    except Exception as e:
        logger.warning("写入 model_acceptance 失败: %s", e)
    finally:
        conn.close()


def get_last_model_for_session(session_id: str) -> Optional[str]:
    """
    从 llm_audit 中查找该 session 最近一次 response 使用的模型。
    用于 apply-patch 时记录是哪个模型被接受了。
    """
    try:
        from backend.services.llm.llm_audit import _get_conn
        conn = _get_conn()
        if conn is None:
            return None
        cur = conn.execute(
            """
            SELECT record FROM llm_audit
            WHERE json_extract(record, '$.session_id') = ? AND json_extract(record, '$.direction') = 'response'
            ORDER BY ts DESC LIMIT 1
            """,
            (session_id,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        rec = json.loads(row[0])
        return rec.get("model")
    except Exception as e:
        logger.debug("get_last_model_for_session: %s", e)
        return None


def get_model_stats(days: int = 30) -> List[Dict[str, Any]]:
    """
    聚合模型统计：响应时间（从 llm_audit）、接受次数（从 model_acceptance）。
    返回按综合得分排名的列表。
    """
    from backend.services.llm.llm_audit import _is_audit_disabled

    if _is_audit_disabled():
        return []

    conn = _get_conn()
    if conn is None:
        return []

    # 时间范围：最近 N 天
    from datetime import timedelta
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    by_model: Dict[str, Dict[str, Any]] = {}

    try:
        # 1. 从 llm_audit 计算响应时间
        cur = conn.execute(
            """
            SELECT ts, record FROM llm_audit
            WHERE ts >= ? AND (record LIKE '%"direction":"request"%' OR record LIKE '%"direction":"response"%')
            ORDER BY ts ASC
            """,
            (cutoff,),
        )
        requests: Dict[str, Dict] = {}  # audit_id -> {ts, model}
        for row in cur.fetchall():
            try:
                rec = json.loads(row[0])
                direction = rec.get("direction")
                model = rec.get("model", "")
                ts = rec.get("ts", "")
                audit_id = rec.get("audit_id") or ""
                if not model or not audit_id:
                    continue
                if direction == "request":
                    requests[audit_id] = {"ts": ts, "model": model}
                elif direction == "response" and audit_id in requests:
                    req = requests[audit_id]
                    if req["model"] == model:
                        try:
                            t1 = datetime.fromisoformat(req["ts"].replace("Z", "+00:00"))
                            t2 = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            duration_ms = (t2 - t1).total_seconds() * 1000
                        except Exception:
                            duration_ms = None
                        if duration_ms is not None and duration_ms >= 0:
                            if model not in by_model:
                                by_model[model] = {"model": model, "call_count": 0, "total_response_ms": 0.0, "accepted_count": 0}
                            by_model[model]["call_count"] += 1
                            by_model[model]["total_response_ms"] += duration_ms
                    del requests[audit_id]
            except (json.JSONDecodeError, KeyError):
                continue

        # 2. 从 model_acceptance 统计接受次数
        cur = conn.execute(
            f"SELECT model, COUNT(*) FROM {ACCEPTANCE_TABLE} WHERE ts >= ? GROUP BY model",
            (cutoff,),
        )
        for row in cur.fetchall():
            model, count = row[0], row[1]
            if model not in by_model:
                by_model[model] = {"model": model, "call_count": 0, "total_response_ms": 0.0, "accepted_count": 0}
            by_model[model]["accepted_count"] = count

    except Exception as e:
        logger.warning("get_model_stats 失败: %s", e)
    finally:
        conn.close()

    # 计算平均值、综合得分并排序
    result = []
    for m, d in by_model.items():
        avg_ms = d["total_response_ms"] / d["call_count"] if d["call_count"] > 0 else None
        # 综合得分：接受次数权重高，平均响应时间越短越好（取倒数）
        accept_score = d["accepted_count"] * 10
        speed_score = (10000 / avg_ms) if avg_ms and avg_ms > 0 else 0
        score = accept_score + speed_score
        result.append({
            "model": d["model"],
            "call_count": d["call_count"],
            "avg_response_ms": round(avg_ms, 1) if avg_ms is not None else None,
            "accepted_count": d["accepted_count"],
            "score": round(score, 1),
        })
    result.sort(key=lambda x: (-x["score"], -x["accepted_count"], x["avg_response_ms"] or 999999))
    return result
