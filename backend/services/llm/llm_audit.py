"""
LLM 对话审计：记录每次送入 LLM 的输入与 LLM 的输出，便于审计与排查。
记录存入 SQLite 数据库（与 sessions、task_queue 同目录），表 llm_audit。
同一次调用的 request / response / response_error 通过 meta.audit_id 关联。

可通过环境变量关闭：LLM_AUDIT_DISABLED=1 或 true/yes 时不写入任何记录。
"""
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_NAME = "llm_audit.db"
TABLE_NAME = "llm_audit"


def _is_audit_disabled() -> bool:
    """环境变量 LLM_AUDIT_DISABLED=1|true|yes 时关闭审计写入。"""
    v = os.environ.get("LLM_AUDIT_DISABLED", "").strip().lower()
    return v in ("1", "true", "yes")


def create_audit_id() -> str:
    """生成单次 LLM 调用的审计关联 ID，用于在日志中配对 request 与 response。"""
    return uuid.uuid4().hex[:16]


# 单条内容在审计中的最大长度（字符），超出截断并注明
MAX_CONTENT_LEN = 50000
# 单条消息预览最大长度
MAX_MESSAGE_PREVIEW_LEN = 8000


def _get_conn():
    """获取 llm_audit 数据库连接并确保表存在。失败返回 None。"""
    try:
        from shared.storage_utils import get_storage_manager
        conn = get_storage_manager().get_sqlite_connection(DB_NAME)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                record TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_audit_ts ON llm_audit(ts)")
        conn.commit()
        return conn
    except Exception as e:
        logger.warning("LLM 审计数据库不可用: %s", e)
        return None


def get_audit_dir() -> Optional[Path]:
    """返回审计存储路径（数据库文件所在路径），供 API 展示。不可用时为 None。"""
    try:
        from shared.storage_utils import get_storage_manager
        return get_storage_manager().get_sqlite_path(DB_NAME)
    except Exception:
        return None


def _get_legacy_audit_dir() -> Optional[Path]:
    """旧版审计目录（JSONL 文件），用于迁移。"""
    try:
        from shared.platform_utils import get_app_data_dir
        return get_app_data_dir() / "llm_audit"
    except Exception:
        return None


def migrate_legacy_jsonl_to_db() -> Tuple[int, Optional[str]]:
    """
    将旧版 llm_audit/ 下的 JSONL 文件迁移到 SQLite，迁移成功后删除这些文件及空目录。
    返回 (迁移条数, 错误信息)，成功时错误为 None。
    """
    legacy_dir = _get_legacy_audit_dir()
    if legacy_dir is None or not legacy_dir.is_dir():
        return 0, None
    files = sorted(legacy_dir.glob("llm_audit_*.jsonl"), key=lambda p: p.name)
    if not files:
        try:
            legacy_dir.rmdir()
        except OSError:
            pass
        return 0, None
    conn = _get_conn()
    if conn is None:
        return 0, "数据库不可用"
    inserted = 0
    try:
        for path in files:
            if not path.is_file():
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        ts = record.get("ts") or ""
                        conn.execute(
                            "INSERT INTO llm_audit (ts, record) VALUES (?, ?)",
                            (ts, json.dumps(record, ensure_ascii=False)),
                        )
                        inserted += 1
                    except (json.JSONDecodeError, Exception) as e:
                        logger.debug("跳过无效行 %s: %s", path.name, e)
            path.unlink()
        conn.commit()
        try:
            if legacy_dir.exists() and not any(legacy_dir.iterdir()):
                legacy_dir.rmdir()
        except OSError:
            pass
        return inserted, None
    except Exception as e:
        logger.warning("迁移审计 JSONL 失败: %s", e)
        return inserted, str(e)
    finally:
        conn.close()


def list_audit_dates() -> List[str]:
    """列出已有审计记录的日期，格式 YYYY-MM-DD，降序（最新在前）。首次调用时会尝试迁移旧版 JSONL 并删除原文件。"""
    migrate_legacy_jsonl_to_db()
    conn = _get_conn()
    if conn is None:
        return []
    try:
        cur = conn.execute(
            "SELECT DISTINCT substr(ts, 1, 10) AS d FROM llm_audit ORDER BY d DESC"
        )
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.warning("列举审计日期失败: %s", e)
        return []
    finally:
        conn.close()


def read_audit_records(
    date: str,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    读取指定日期的审计记录，按时间倒序（最新在前），分页。
    返回 (records, total)。
    """
    conn = _get_conn()
    if conn is None:
        return [], 0
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM llm_audit WHERE substr(ts, 1, 10) = ?",
            (date,),
        )
        total = cur.fetchone()[0]
        cur = conn.execute(
            """
            SELECT record FROM llm_audit
            WHERE substr(ts, 1, 10) = ?
            ORDER BY ts DESC
            LIMIT ? OFFSET ?
            """,
            (date, limit, offset),
        )
        records = []
        for row in cur.fetchall():
            try:
                records.append(json.loads(row[0]))
            except json.JSONDecodeError:
                continue
        return records, total
    except Exception as e:
        logger.warning("读取审计记录失败: %s", e)
        return [], 0
    finally:
        conn.close()


def get_daily_token_stats(from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """
    按日聚合 token 消耗（仅统计 direction=response 且含 usage 的记录）。
    返回 [{date, prompt_tokens, completion_tokens, total_tokens, call_count}, ...]，按日期降序。
    """
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    conn = _get_conn()
    if conn is None:
        return []
    try:
        cur = conn.execute(
            """
            SELECT record FROM llm_audit
            WHERE substr(ts, 1, 10) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        )
        by_date: Dict[str, Dict[str, int]] = {}
        for row in cur.fetchall():
            try:
                rec = json.loads(row[0])
                if rec.get("direction") != "response":
                    continue
                usage = rec.get("usage")
                if not usage or not isinstance(usage, dict):
                    continue
                date_str = (rec.get("ts") or "")[:10]
                if not date_str:
                    continue
                if date_str not in by_date:
                    by_date[date_str] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "call_count": 0}
                d = by_date[date_str]
                d["call_count"] += 1
                d["prompt_tokens"] += usage.get("prompt_tokens") or 0
                d["completion_tokens"] += usage.get("completion_tokens") or 0
                d["total_tokens"] += usage.get("total_tokens") or 0
            except (json.JSONDecodeError, TypeError):
                continue
        return [
            {"date": d, "prompt_tokens": v["prompt_tokens"], "completion_tokens": v["completion_tokens"], "total_tokens": v["total_tokens"], "call_count": v["call_count"]}
            for d, v in sorted(by_date.items(), reverse=True)
        ]
    except Exception as e:
        logger.warning("按日聚合 token 消耗失败: %s", e)
        return []
    finally:
        conn.close()


def read_audit_records_range(
    from_date: str,
    to_date: str,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    读取时间区间内的审计记录（from_date 至 to_date 含），按 ts 倒序，分页。
    返回 (records, total)。
    """
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    conn = _get_conn()
    if conn is None:
        return [], 0
    try:
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM llm_audit
            WHERE substr(ts, 1, 10) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        )
        total = cur.fetchone()[0]
        cur = conn.execute(
            """
            SELECT record FROM llm_audit
            WHERE substr(ts, 1, 10) BETWEEN ? AND ?
            ORDER BY ts DESC
            LIMIT ? OFFSET ?
            """,
            (from_date, to_date, limit, offset),
        )
        records = []
        for row in cur.fetchall():
            try:
                records.append(json.loads(row[0]))
            except json.JSONDecodeError:
                continue
        return records, total
    except Exception as e:
        logger.warning("读取审计记录失败: %s", e)
        return [], 0
    finally:
        conn.close()


def _truncate(s: str, max_len: int = MAX_CONTENT_LEN) -> str:
    if not s or len(s) <= max_len:
        return s or ""
    return s[:max_len] + "\n...(已截断)"


def _messages_summary(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """将 messages 转为可序列化、长度受控的摘要，用于审计。"""
    out = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content") or m.get("text") or ""
        if isinstance(content, str):
            preview = _truncate(content, MAX_MESSAGE_PREVIEW_LEN)
        else:
            s = str(content)
            preview = s[:MAX_MESSAGE_PREVIEW_LEN] + ("...(已截断)" if len(s) > MAX_MESSAGE_PREVIEW_LEN else "")
        out.append({
            "role": role,
            "content_length": len(str(content)),
            "content_preview": preview,
        })
    return {"message_count": len(messages), "messages": out}


def _response_summary(content: Any, model: str) -> Dict[str, Any]:
    """将 LLM 返回内容转为可序列化的摘要。"""
    if content is None:
        return {"type": "null"}
    if isinstance(content, str):
        return {
            "type": "text",
            "content_length": len(content),
            "content_preview": _truncate(content, MAX_CONTENT_LEN),
        }
    # 可能是 message 对象（含 tool_calls）
    if hasattr(content, "content") and content.content:
        return {
            "type": "text",
            "content_length": len(content.content),
            "content_preview": _truncate(content.content, MAX_CONTENT_LEN),
        }
    if hasattr(content, "tool_calls") and content.tool_calls:
        names = [
            getattr(t, "function", None) and getattr(t.function, "name", None) or str(t)
            for t in content.tool_calls
        ]
        return {"type": "tool_calls", "count": len(content.tool_calls), "names": names}
    return {"type": "other", "repr": _truncate(repr(content), 2000)}


def append_audit(
    direction: str,
    model: str,
    payload: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    追加一条 LLM 审计记录到数据库。失败仅打日志，不抛异常。
    LLM_AUDIT_DISABLED=1 时不写入。

    Args:
        direction: "request" | "response" | "response_error"
        model: 模型名
        payload: 请求时为 messages 摘要，响应时为 content 摘要
        meta: 可选，如 session_id, usage, error
    """
    if _is_audit_disabled():
        return
    conn = _get_conn()
    if conn is None:
        return
    ts = datetime.utcnow().isoformat() + "Z"
    record = {
        "ts": ts,
        "direction": direction,
        "model": model,
        "payload": payload,
        **(meta or {}),
    }
    try:
        conn.execute(
            "INSERT INTO llm_audit (ts, record) VALUES (?, ?)",
            (ts, json.dumps(record, ensure_ascii=False)),
        )
        conn.commit()
    except Exception as e:
        logger.warning("写入 LLM 审计日志失败: %s", e)
    finally:
        conn.close()
