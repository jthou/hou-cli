"""
FTS5 任务检索 SQL 行为单测（仅 sqlite3 + fts5_match，不依赖 chromadb / TaskQueueDB）。

时间：2026-03-14；理由：CI/本地可能未装全量依赖；方法：内存库复刻 tasks + tasks_fts + 触发器与 search_completed_tasks_fts 等价 SQL。
"""
import sqlite3

import pytest

from backend.infrastructure.storage.fts5_match import build_fts5_match_query


def _has_fts5() -> bool:
    c = sqlite3.connect(":memory:")
    try:
        return c.execute("SELECT sqlite_compileoption_used('ENABLE_FTS5')").fetchone()[0] == 1
    finally:
        c.close()


@pytest.mark.skipif(not _has_fts5(), reason="SQLite 未编译 FTS5")
def test_fts5_bm25_search_matches_body_like_task_queue():
    conn = sqlite3.connect(":memory:")
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                result TEXT,
                deleted_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE VIRTUAL TABLE tasks_fts USING fts5(
                task_id UNINDEXED,
                body,
                tokenize = 'unicode61'
            )
            """
        )
        cur.execute(
            """
            CREATE TRIGGER trg_tasks_fts_ai AFTER INSERT ON tasks BEGIN
              INSERT INTO tasks_fts(task_id, body) VALUES (
                NEW.task_id,
                trim(
                  COALESCE(NEW.task_name, '') || ' ' || COALESCE(NEW.task_type, '') || ' ' ||
                  COALESCE(NEW.message, '')
                )
              );
            END
            """
        )
        cur.execute(
            """
            CREATE TRIGGER trg_tasks_fts_au AFTER UPDATE ON tasks BEGIN
              DELETE FROM tasks_fts WHERE task_id = NEW.task_id;
              INSERT INTO tasks_fts(task_id, body) VALUES (
                NEW.task_id,
                trim(
                  COALESCE(NEW.task_name, '') || ' ' || COALESCE(NEW.task_type, '') || ' ' ||
                  COALESCE(NEW.message, '')
                )
              );
            END
            """
        )

        cur.execute(
            """
            INSERT INTO tasks(task_id, task_type, task_name, status, message, result, deleted_at)
            VALUES ('a', 'url_to_wiki', '甲', 'completed', NULL, ?, NULL)
            """,
            ('{"summary": "已经同步 wiki 页面", "data": {}}',),
        )
        cur.execute(
            """
            INSERT INTO tasks(task_id, task_type, task_name, status, message, result, deleted_at)
            VALUES ('b', 'noop', '乙', 'completed', NULL, ?, NULL)
            """,
            ('{"summary": "无关", "data": {}}',),
        )
        conn.commit()

        mq = build_fts5_match_query("wiki")
        assert mq
        cur.execute(
            """
            SELECT t.task_id
            FROM tasks_fts
            INNER JOIN tasks AS t ON t.task_id = tasks_fts.task_id
            WHERE tasks_fts MATCH ?
              AND t.status = 'completed'
              AND (t.deleted_at IS NULL)
            ORDER BY bm25(tasks_fts)
            LIMIT ?
            """,
            (mq, 10),
        )
        ids = [r[0] for r in cur.fetchall()]
        assert "a" in ids
        assert ids[0] == "a"
    finally:
        conn.close()
