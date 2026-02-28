"""add task queue pipeline and deleted columns

Revision ID: 20250227000000
Revises:
Create Date: 2025-02-27

任务队列表 tasks 补列（与 _init_db 中逻辑一致，幂等）：
depends_on_task_id, input_bindings, pipeline_id, deleted_at
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250227000000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tasks_table_exists(conn):
    """tasks 表是否存在（应用 _init_db 可能尚未运行）"""
    cursor = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"))
    return cursor.fetchone() is not None


def _task_columns(conn):
    """返回 tasks 表当前列名列表"""
    cursor = conn.execute(sa.text("PRAGMA table_info(tasks)"))
    return [row[1] for row in cursor.fetchall()]


def upgrade() -> None:
    conn = op.get_bind()
    if not _tasks_table_exists(conn):
        # 全新库：表由应用首次启动时 _init_db 创建，此处仅跳过
        return
    cols = _task_columns(conn)
    if "depends_on_task_id" not in cols:
        op.execute("ALTER TABLE tasks ADD COLUMN depends_on_task_id TEXT")
    if "input_bindings" not in cols:
        op.execute("ALTER TABLE tasks ADD COLUMN input_bindings TEXT")
    if "pipeline_id" not in cols:
        op.execute("ALTER TABLE tasks ADD COLUMN pipeline_id TEXT")
    if "deleted_at" not in cols:
        op.execute("ALTER TABLE tasks ADD COLUMN deleted_at TEXT")


def downgrade() -> None:
    # SQLite 旧版本不支持 DROP COLUMN，且应用层 _init_db 会按需补列，此处不实现回退
    pass
