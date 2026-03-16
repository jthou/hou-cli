"""
接受修改记录与打分服务（时间：2025-03-15；理由：记录用户接受修改、抽样打分、持续改进写作画像；方法：SQLite 存储 + API）

流程：
1. 用户点击「接受修改」→ 记录 (original, ai_content, accepted_content)
2. 系统从记录中抽样章节，请用户打分
3. 根据高分内容更新写作画像
"""
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


def _get_db_path() -> Path:
    """与 article_revisions 同目录"""
    try:
        from shared.storage_utils import get_storage_manager
        base = get_storage_manager().get_sqlite_path("article_revisions.db")
        if base:
            return base.parent / "writing_acceptance.db"
    except Exception:
        pass
    return Path.cwd() / "data" / "writing_acceptance.db"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS acceptance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_id TEXT,
            original_content TEXT,
            ai_content TEXT NOT NULL,
            accepted_content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_acceptance_session ON acceptance_records(session_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_acceptance_created ON acceptance_records(created_at DESC)"
    )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS section_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            section_index INTEGER NOT NULL,
            section_text TEXT,
            score INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (record_id) REFERENCES acceptance_records(id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ratings_record ON section_ratings(record_id)"
    )
    # 时间：2025-03-15；理由：每条助手回复可打分+理由，供系统提示词注入；方法：message_ratings 表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS message_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_msg_ratings_session ON message_ratings(session_id)"
    )


def record_acceptance(
    session_id: str,
    ai_content: str,
    accepted_content: str,
    original_content: Optional[str] = None,
    message_id: Optional[str] = None,
) -> Optional[int]:
    """记录一次接受修改。返回 record_id。"""
    path = _get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        _init_db(conn)
        cur = conn.execute(
            """
            INSERT INTO acceptance_records
            (session_id, message_id, original_content, ai_content, accepted_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                message_id or "",
                original_content or "",
                ai_content or "",
                accepted_content or "",
                datetime.utcnow().isoformat() + "Z",
            ),
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        logger.warning("写入接受记录失败: %s", e)
        conn.rollback()
        return None
    finally:
        conn.close()


def _split_sections(content: str) -> List[str]:
    """按 ## 或 ### 分割为章节，保留标题+内容。"""
    if not (content or "").strip():
        return []
    parts = re.split(r"^(#{1,6}\s+.+)$", content, flags=re.MULTILINE)
    sections = []
    for i, p in enumerate(parts):
        p = (p or "").strip()
        if not p:
            continue
        if p.startswith("#"):
            sections.append(p)
        elif sections:
            sections[-1] = sections[-1] + "\n\n" + p
        else:
            sections.append(p)
    return [s for s in sections if s.strip()]


def _get_conn():
    path = _get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    _init_db(conn)
    return conn


def list_records_for_rating(limit: int = 20) -> List[dict]:
    """获取未打分或已打分较少的记录，用于抽样。"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT r.id, r.session_id, r.accepted_content, r.created_at,
                   COUNT(s.id) as rated_count
            FROM acceptance_records r
            LEFT JOIN section_ratings s ON r.id = s.record_id
            GROUP BY r.id
            HAVING LENGTH(r.accepted_content) > 200
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "accepted_content": r[2],
                "created_at": r[3],
                "rated_count": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_sections_for_rating(record_id: int, max_sections: int = 5) -> List[dict]:
    """
    从某条记录中抽取章节供打分。
    返回：章节列表，含 section_index、section_text、是否已打分。
    """
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT accepted_content FROM acceptance_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            return []
        content = row[0] or ""
        sections = _split_sections(content)
        if not sections:
            sections = [content[:2000]] if content else []

        # 已打分的 section_index
        rated = set(
            r[0]
            for r in conn.execute(
                "SELECT section_index FROM section_ratings WHERE record_id = ?",
                (record_id,),
            ).fetchall()
        )

        # 优先选未打分的，截断到 max_sections
        result = []
        for i, text in enumerate(sections[: max_sections * 2]):
            if len(result) >= max_sections:
                break
            text = (text or "").strip()
            if len(text) < 50:
                continue
            if len(text) > 1500:
                text = text[:1500] + "\n…（已截断）"
            result.append({
                "section_index": i,
                "section_text": text,
                "rated": i in rated,
            })
        return result
    finally:
        conn.close()


def submit_section_rating(
    record_id: int,
    section_index: int,
    score: int,
    section_text: Optional[str] = None,
) -> bool:
    """提交章节打分。score 建议 1-5。"""
    if not 1 <= score <= 5:
        return False
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO section_ratings (record_id, section_index, section_text, score, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record_id,
                section_index,
                section_text or "",
                score,
                datetime.utcnow().isoformat() + "Z",
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning("提交打分失败: %s", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def record_message_rating(
    session_id: str,
    message_id: str,
    score: int,
    reason: Optional[str] = None,
) -> bool:
    """记录对某条助手回复的打分及理由。score 1-5。"""
    if not 1 <= score <= 5:
        return False
    path = _get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        _init_db(conn)
        conn.execute(
            """
            INSERT INTO message_ratings (session_id, message_id, score, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                message_id or "",
                score,
                reason or "",
                datetime.utcnow().isoformat() + "Z",
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning("写入消息打分失败: %s", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def get_message_ratings_for_session(session_id: str, limit: int = 20) -> List[dict]:
    """获取某会话的历史打分（含理由），用于注入系统提示词。"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT message_id, score, reason, created_at
            FROM message_ratings
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        return [
            {"message_id": r[0], "score": r[1], "reason": r[2] or "", "created_at": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def get_high_rated_content(min_score: int = 4, limit: int = 10) -> List[str]:
    """获取高分章节内容，用于更新写作画像。同一 record+section 只取最新一次打分。"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT record_id, section_index, section_text, score, created_at
            FROM section_ratings WHERE score >= ?
            ORDER BY score DESC, created_at DESC
            """,
            (min_score,),
        ).fetchall()
        seen = set()
        result = []
        for r in rows:
            key = (r[0], r[1])
            if key in seen:
                continue
            seen.add(key)
            text = (r[2] or "").strip()
            if text:
                result.append(r[2] or "")
            if len(result) >= limit:
                break
        return result
    finally:
        conn.close()
