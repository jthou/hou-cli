"""定时任务数据库方法测试"""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from backend.infrastructure.storage.task_queue_db import TaskQueueDB


@pytest.fixture
def temp_sched_db():
    """临时任务队列 DB（含 scheduled_tasks）"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = TaskQueueDB(db_name=os.path.basename(path))
    db.db_path = Path(path)
    db._init_db()
    yield db
    if os.path.exists(path):
        os.unlink(path)


class TestScheduledTasks:
    def test_create_scheduled_task_interval(self, temp_sched_db):
        sid = temp_sched_db.create_scheduled_task(
            task_type="weather_query",
            task_name="每小时天气",
            schedule_type="interval",
            schedule_config={"interval_seconds": 3600},
            metadata={"location": "北京"},
        )
        assert sid
        tasks = temp_sched_db.list_scheduled_tasks(active_only=False)
        assert len(tasks) == 1
        assert tasks[0]["task_type"] == "weather_query"
        assert tasks[0]["schedule_config"]["interval_seconds"] == 3600
        assert tasks[0]["consecutive_errors"] == 0

    def test_create_scheduled_task_cron(self, temp_sched_db):
        sid = temp_sched_db.create_scheduled_task(
            task_type="weather_query",
            task_name="每天天气",
            schedule_type="cron",
            schedule_config={"cron": "0 8 * * *"},
            metadata={"location": "上海"},
        )
        assert sid
        tasks = temp_sched_db.list_scheduled_tasks(active_only=False)
        assert len(tasks) == 1
        assert tasks[0]["schedule_config"]["cron"] == "0 8 * * *"

    def test_get_due_scheduled_tasks_empty(self, temp_sched_db):
        due = temp_sched_db.get_due_scheduled_tasks()
        assert due == []

    def test_get_due_scheduled_tasks_with_due(self, temp_sched_db):
        sid = temp_sched_db.create_scheduled_task(
            task_type="weather_query",
            task_name="测试",
            schedule_type="interval",
            schedule_config={"interval_seconds": 60},
            metadata={},
        )
        # 将 next_run_time 设为过去（用 SQLite 表达式确保可比）
        conn = temp_sched_db._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE scheduled_tasks SET next_run_time = datetime('now', '-1 hour') "
            "WHERE schedule_id = ?",
            (sid,),
        )
        conn.commit()
        conn.close()

        due = temp_sched_db.get_due_scheduled_tasks()
        assert len(due) == 1
        assert due[0]["schedule_id"] == sid

    def test_update_after_success(self, temp_sched_db):
        sid = temp_sched_db.create_scheduled_task(
            task_type="weather_query",
            task_name="测试",
            schedule_type="interval",
            schedule_config={"interval_seconds": 3600},
            metadata={},
        )
        now = datetime.now().isoformat()
        ok = temp_sched_db.update_scheduled_task_after_success(
            schedule_id=sid,
            schedule_type="interval",
            schedule_config={"interval_seconds": 3600},
            last_run_time=now,
        )
        assert ok
        tasks = temp_sched_db.list_scheduled_tasks(active_only=False)
        assert tasks[0]["last_run_time"] == now
        assert tasks[0]["consecutive_errors"] == 0

    def test_update_on_failure(self, temp_sched_db):
        sid = temp_sched_db.create_scheduled_task(
            task_type="weather_query",
            task_name="测试",
            schedule_type="interval",
            schedule_config={"interval_seconds": 3600},
            metadata={},
        )
        ok = temp_sched_db.update_scheduled_task_on_failure(
            schedule_id=sid,
            error="校验失败",
        )
        assert ok
        tasks = temp_sched_db.list_scheduled_tasks(active_only=False)
        assert tasks[0]["consecutive_errors"] == 1
        assert "校验失败" in (tasks[0]["last_error"] or "")

    def test_toggle_and_delete(self, temp_sched_db):
        sid = temp_sched_db.create_scheduled_task(
            task_type="weather_query",
            task_name="测试",
            schedule_type="interval",
            schedule_config={"interval_seconds": 3600},
            metadata={},
        )
        temp_sched_db.toggle_scheduled_task(sid, False)
        tasks = temp_sched_db.list_scheduled_tasks(active_only=True)
        assert len(tasks) == 0
        tasks_all = temp_sched_db.list_scheduled_tasks(active_only=False)
        assert tasks_all[0]["is_active"] is False

        temp_sched_db.delete_scheduled_task(sid)
        assert len(temp_sched_db.list_scheduled_tasks(active_only=False)) == 0
