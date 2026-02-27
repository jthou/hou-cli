"""add scheduled task columns and tasks created_by_schedule_id

Revision ID: 20250227100000
Revises: 20250227000000
Create Date: 2025-02-27

- tasks: created_by_schedule_id（溯源定时任务）
- scheduled_tasks: consecutive_errors, last_error（错误退避）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250227100000"
down_revision: Union[str, None] = "20250227000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name):
    cursor = conn.execute(sa.text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}'"))
    return cursor.fetchone() is not None


def _columns(conn, table):
    cursor = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return [row[1] for row in cursor.fetchall()]


def upgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, "tasks"):
        cols = _columns(conn, "tasks")
        if "created_by_schedule_id" not in cols:
            op.execute("ALTER TABLE tasks ADD COLUMN created_by_schedule_id TEXT")

    if _table_exists(conn, "scheduled_tasks"):
        cols = _columns(conn, "scheduled_tasks")
        if "consecutive_errors" not in cols:
            op.execute("ALTER TABLE scheduled_tasks ADD COLUMN consecutive_errors INTEGER DEFAULT 0")
        if "last_error" not in cols:
            op.execute("ALTER TABLE scheduled_tasks ADD COLUMN last_error TEXT")


def downgrade() -> None:
    # SQLite 不支持 DROP COLUMN，应用层 _init_db 会按需补列
    pass
