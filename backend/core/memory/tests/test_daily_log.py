"""DailyLogMemory 单元测试"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from backend.core.memory.short_term.daily_log import DailyLogMemory


@pytest.fixture
def temp_storage(tmp_path):
    """临时存储目录"""
    return tmp_path / "memory"


@pytest.fixture
def daily_log(temp_storage):
    """DailyLogMemory 实例"""
    return DailyLogMemory(storage_dir=temp_storage)


class TestDailyLogMemory:
    """DailyLogMemory 测试"""

    def test_write_and_read_today(self, daily_log, temp_storage):
        """写入并读取当日日志"""
        ok = daily_log.write_daily_entry("测试内容 A")
        assert ok is True
        path = temp_storage / (datetime.now().strftime("%Y-%m-%d") + ".md")
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "测试内容 A" in text

    def test_append_multiple(self, daily_log):
        """多次 append 到同一天"""
        daily_log.write_daily_entry("第一条")
        daily_log.write_daily_entry("第二条")
        block = daily_log.get_recent_entries(hours=48)
        assert "第一条" in block
        assert "第二条" in block

    def test_get_recent_empty(self, daily_log):
        """无内容时返回空字符串"""
        block = daily_log.get_recent_entries(hours=48)
        assert block == ""

    def test_get_recent_48h(self, daily_log, temp_storage):
        """获取最近 48 小时包含今天和昨天"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        (temp_storage / f"{yesterday.strftime('%Y-%m-%d')}.md").write_text("昨天日志")
        (temp_storage / f"{today.strftime('%Y-%m-%d')}.md").write_text("今天日志")
        block = daily_log.get_recent_entries(hours=48)
        assert "昨天日志" in block
        assert "今天日志" in block
