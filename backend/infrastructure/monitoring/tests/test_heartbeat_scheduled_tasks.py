"""心跳 check_scheduled_tasks 逻辑测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.infrastructure.monitoring.heartbeat import HeartbeatMonitor


@pytest.fixture
def monitor():
    return HeartbeatMonitor(interval=30)


@pytest.mark.asyncio
async def test_check_scheduled_tasks_empty(monitor):
    """无到期任务时直接返回"""
    mock_db = MagicMock()
    mock_db.get_due_scheduled_tasks.return_value = []

    await monitor.check_scheduled_tasks(mock_db)

    mock_db.get_due_scheduled_tasks.assert_called_once()
    mock_db.create_task.assert_not_called()
    mock_db.update_scheduled_task_after_success.assert_not_called()
    mock_db.update_scheduled_task_on_failure.assert_not_called()


@pytest.mark.asyncio
async def test_check_scheduled_tasks_success(monitor):
    """到期任务校验通过时创建任务并更新成功状态"""
    mock_db = MagicMock()
    mock_db.get_due_scheduled_tasks.return_value = [
        {
            "schedule_id": "sched-1",
            "task_type": "weather_query",
            "task_name": "每小时天气",
            "schedule_type": "interval",
            "schedule_config": {"interval_seconds": 3600},
            "metadata": {"location": "北京", "query_type": "current"},
        },
    ]
    mock_db.create_task.return_value = "task-123"

    with patch("backend.infrastructure.execution.task_handlers.validate_task_creation", return_value=(True, None)):
        await monitor.check_scheduled_tasks(mock_db)

    mock_db.create_task.assert_called_once()
    call_kw = mock_db.create_task.call_args[1]
    assert call_kw["task_type"] == "weather_query"
    assert call_kw["metadata"]["location"] == "北京"
    assert call_kw["created_by_schedule_id"] == "sched-1"

    mock_db.update_scheduled_task_after_success.assert_called_once()
    call_kw2 = mock_db.update_scheduled_task_after_success.call_args[1]
    assert call_kw2["schedule_id"] == "sched-1"
    assert call_kw2["schedule_type"] == "interval"

    mock_db.update_scheduled_task_on_failure.assert_not_called()


@pytest.mark.asyncio
async def test_check_scheduled_tasks_validation_fails(monitor):
    """校验失败时调用 update_scheduled_task_on_failure"""
    mock_db = MagicMock()
    mock_db.get_due_scheduled_tasks.return_value = [
        {
            "schedule_id": "sched-2",
            "task_type": "weather_query",
            "task_name": "无效",
            "schedule_type": "interval",
            "schedule_config": {"interval_seconds": 3600},
            "metadata": {},  # 缺少 location
        },
    ]

    with patch("backend.infrastructure.execution.task_handlers.validate_task_creation", return_value=(False, "location 必填")):
        await monitor.check_scheduled_tasks(mock_db)

    mock_db.create_task.assert_not_called()
    mock_db.update_scheduled_task_after_success.assert_not_called()
    mock_db.update_scheduled_task_on_failure.assert_called_once_with(
        schedule_id="sched-2",
        error="location 必填",
    )


@pytest.mark.asyncio
async def test_check_scheduled_tasks_create_raises(monitor):
    """create_task 抛异常时调用 update_scheduled_task_on_failure"""
    mock_db = MagicMock()
    mock_db.get_due_scheduled_tasks.return_value = [
        {
            "schedule_id": "sched-3",
            "task_type": "weather_query",
            "task_name": "测试",
            "schedule_type": "interval",
            "schedule_config": {"interval_seconds": 3600},
            "metadata": {"location": "北京"},
        },
    ]
    mock_db.create_task.side_effect = Exception("DB 写入失败")

    with patch("backend.infrastructure.execution.task_handlers.validate_task_creation", return_value=(True, None)):
        await monitor.check_scheduled_tasks(mock_db)

    mock_db.create_task.assert_called_once()
    mock_db.update_scheduled_task_after_success.assert_not_called()
    mock_db.update_scheduled_task_on_failure.assert_called_once_with(
        schedule_id="sched-3",
        error="DB 写入失败",
    )
