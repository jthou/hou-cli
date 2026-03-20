"""短期记忆：每日日志（memory/YYYY-MM-DD.md）

设计文档：docs/design/01-three-level-memory-and-context-design.md
存储位置：get_app_data_dir()/contexts/memory/YYYY-MM-DD.md
"""
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class DailyLogMemory:
    """短期记忆 - 每日日志，append-only"""

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Args:
            storage_dir: 存储目录，默认 get_app_data_dir()/contexts/memory
        """
        if storage_dir is None:
            from shared.platform_utils import get_app_data_dir
            storage_dir = get_app_data_dir() / "contexts" / "memory"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, date: Optional[datetime] = None) -> Path:
        """获取指定日期的日志文件路径"""
        dt = date or datetime.now()
        return self.storage_dir / f"{dt.strftime('%Y-%m-%d')}.md"

    def write_daily_entry(self, content: str, date: Optional[datetime] = None) -> bool:
        """按日期 append 到 YYYY-MM-DD.md

        Args:
            content: 要追加的内容（可含多行）
            date: 日期，默认今天

        Returns:
            是否写入成功
        """
        try:
            path = self._get_file_path(date)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                ts = (date or datetime.now()).strftime("%H:%M")
                f.write(f"\n## {ts}\n\n{content.strip()}\n")
            return True
        except (OSError, IOError) as e:
            import logging
            logging.getLogger(__name__).warning("DailyLogMemory.write_daily_entry 失败: %s", e)
            return False

    def get_recent_entries(self, hours: int = 48) -> str:
        """获取最近 N 小时的日志内容

        Args:
            hours: 小时数，默认 48（今天+昨天）

        Returns:
            合并后的 Markdown 文本，无内容时返回空字符串
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        parts = []
        current = datetime.now().date()
        # 最多取 3 天（48h 覆盖约 2 天）
        for _ in range(3):
            dt = datetime.combine(current, datetime.min.time())
            if dt < cutoff:
                break
            path = self._get_file_path(dt)
            if path.exists():
                try:
                    text = path.read_text(encoding="utf-8").strip()
                    if text:
                        parts.append(f"### {current}\n\n{text}")
                except (OSError, IOError):
                    pass
            current = (datetime.combine(current, datetime.min.time()) - timedelta(days=1)).date()
        return "\n\n".join(reversed(parts)) if parts else ""
