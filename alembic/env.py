"""
Alembic 环境：任务队列 SQLite 迁移。
使用与 backend 相同的 DB 路径（get_storage_manager().get_sqlite_path("task_queue.db")）。
无 SQLAlchemy Model，迁移脚本内用 op.execute() 执行 raw SQL。
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# 将项目根目录加入 path，以便导入 shared
import sys
from pathlib import Path
_sys_path_insert = Path(__file__).resolve().parents[1]
if str(_sys_path_insert) not in sys.path:
    sys.path.insert(0, str(_sys_path_insert))

from shared.storage_utils import get_storage_manager

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_sqlite_url():
    """与 task_queue_db 一致：使用 StorageManager 的 task_queue.db 路径"""
    path = get_storage_manager().get_sqlite_path("task_queue.db")
    return f"sqlite:///{path}"


def run_migrations_offline():
    """离线模式：仅生成 SQL，不连库"""
    url = get_sqlite_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """在线模式：连接 DB 执行迁移（部署时 alembic upgrade head）"""
    url = get_sqlite_url()
    connectable = create_engine(url)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
