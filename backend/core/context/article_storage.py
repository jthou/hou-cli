"""
写文章会话的「当前文章」与修改历史（版本）存储。
文章内容与历史版本存入 SQLite，便于持续更新与回溯。
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

def _get_article_db_path() -> Optional[Path]:
    """文章库路径：与 sessions/task_queue 同目录下的 article_revisions.db"""
    try:
        from shared.storage_utils import get_storage_manager
        return get_storage_manager().get_sqlite_path("article_revisions.db")
    except Exception:
        return None


class ArticleRevisionStorage:
    """
    文章当前内容 + 修改历史（按会话）。
    当前文章 = 该会话最新一条 revision 的 content。
    """

    def __init__(self, db_path: Optional[Path] = None):
        path = Path(db_path) if db_path else _get_article_db_path()
        if path is None:
            raise RuntimeError("article_revisions db path not available")
        self.db_path = path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS article_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_revisions_session "
                "ON article_revisions(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_revisions_created "
                "ON article_revisions(created_at DESC)"
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS article_wechat_metadata (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    digest TEXT,
                    author TEXT,
                    thumb_media_id TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def get_current(self, session_id: str) -> Optional[str]:
        """当前文章内容 = 该会话最新一条 revision 的 content。"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                """
                SELECT content FROM article_revisions
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def set_current(
        self,
        session_id: str,
        content: str,
        source: str = "user",
    ) -> bool:
        """
        追加一条 revision 作为新的「当前文章」。
        source: 'user' | 'agent'
        """
        if source not in ("user", "agent"):
            source = "user"
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO article_revisions (session_id, content, source, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, content or "", source, datetime.utcnow().isoformat() + "Z"),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_revisions(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Tuple[int, str, str, str]]:
        """
        按时间倒序列出该会话的版本。
        返回 [(id, content, source, created_at), ...]
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT id, content, source, created_at
                FROM article_revisions
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset),
            ).fetchall()
            return list(rows)
        finally:
            conn.close()

    def get_revision(self, revision_id: int, session_id: str) -> Optional[str]:
        """取指定版本的 content；校验 session_id 归属。"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT content FROM article_revisions WHERE id = ? AND session_id = ?",
                (revision_id, session_id),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def clear_session(self, session_id: str) -> bool:
        """删除该会话的全部文章版本（清空会话时调用）。"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM article_revisions WHERE session_id = ?", (session_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def restore_revision(self, revision_id: int, session_id: str) -> Optional[str]:
        """
        将指定版本恢复为当前文章（即再插一条 content 相同的 revision，source=user）。
        返回恢复后的 content。
        """
        content = self.get_revision(revision_id, session_id)
        if content is None:
            return None
        if self.set_current(session_id, content, source="user"):
            return content
        return None

    def get_wechat_metadata(self, session_id: str) -> Optional[dict]:
        """获取会话的公众号文章元数据（标题、摘要、作者、封面 media_id）。"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT title, digest, author, thumb_media_id FROM article_wechat_metadata WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "title": row[0] or "",
                "digest": row[1] or "",
                "author": row[2] or "",
                "thumb_media_id": row[3] or "",
            }
        finally:
            conn.close()

    def set_wechat_metadata(
        self,
        session_id: str,
        title: str = "",
        digest: str = "",
        author: str = "",
        thumb_media_id: str = "",
    ) -> bool:
        """保存会话的公众号文章元数据。"""
        from datetime import datetime

        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO article_wechat_metadata (session_id, title, digest, author, thumb_media_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    title = excluded.title,
                    digest = excluded.digest,
                    author = excluded.author,
                    thumb_media_id = excluded.thumb_media_id,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    (title or "").strip(),
                    (digest or "").strip()[:120],
                    (author or "").strip()[:16],
                    (thumb_media_id or "").strip(),
                    datetime.utcnow().isoformat() + "Z",
                ),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
