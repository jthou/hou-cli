"""定时任务调度计算模块测试"""
import pytest
from datetime import datetime

from backend.infrastructure.schedule import (
    compute_next_run_time,
    error_backoff_seconds,
)


class TestErrorBackoff:
    def test_backoff_increases(self):
        assert error_backoff_seconds(1) == 30
        assert error_backoff_seconds(2) == 60
        assert error_backoff_seconds(3) == 5 * 60
        assert error_backoff_seconds(4) == 15 * 60
        assert error_backoff_seconds(5) == 60 * 60
        assert error_backoff_seconds(10) == 60 * 60

    def test_backoff_zero_safe(self):
        assert error_backoff_seconds(0) == 30  # idx=max(0,-1)=0


class TestComputeNextRunTime:
    def test_interval_first_run(self):
        """首次立即执行：next_run = now"""
        now = datetime(2025, 2, 27, 10, 30)
        next_run = compute_next_run_time(
            schedule_type="interval",
            schedule_config={"interval_seconds": 3600},
            last_run_time=None,
            created_at="2025-02-27T10:00:00",
            now=now,
        )
        assert "2025-02-27" in next_run
        assert "10:30" in next_run  # 立即执行，返回 now

    def test_interval_after_run(self):
        now = datetime(2025, 2, 27, 11, 30)
        next_run = compute_next_run_time(
            schedule_type="interval",
            schedule_config={"interval_seconds": 3600},
            last_run_time="2025-02-27T11:00:00",
            created_at="2025-02-27T10:00:00",
            now=now,
        )
        assert "12:00" in next_run

    def test_cron_next(self):
        now = datetime(2025, 2, 27, 1, 0)
        next_run = compute_next_run_time(
            schedule_type="cron",
            schedule_config={"cron": "0 2 * * *"},
            last_run_time=None,
            created_at="2025-02-27T00:00:00",
            now=now,
        )
        assert "2025-02-27" in next_run
        assert "02:00" in next_run

    def test_invalid_schedule_type(self):
        with pytest.raises(ValueError, match="不支持的 schedule_type"):
            compute_next_run_time(
                schedule_type="invalid",
                schedule_config={},
                last_run_time=None,
                created_at="2025-02-27T10:00:00",
            )
