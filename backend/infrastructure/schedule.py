"""定时任务调度计算模块（时间统一 UTC）"""
from datetime import datetime, timedelta
from typing import Optional

from shared.time_utils import utc_now

# 错误退避时间表（秒）
ERROR_BACKOFF_SECONDS = [
    30,       # 1 次失败 → 30 秒
    60,       # 2 次失败 → 1 分钟
    5 * 60,   # 3 次失败 → 5 分钟
    15 * 60,  # 4 次失败 → 15 分钟
    60 * 60,  # 5+ 次失败 → 60 分钟
]


def error_backoff_seconds(consecutive_errors: int) -> int:
    """根据连续失败次数返回退避秒数"""
    idx = min(max(0, consecutive_errors - 1), len(ERROR_BACKOFF_SECONDS) - 1)
    return ERROR_BACKOFF_SECONDS[idx]


def compute_next_run_time(
    schedule_type: str,
    schedule_config: dict,
    last_run_time: Optional[str],
    created_at: str,
    now: Optional[datetime] = None,
) -> str:
    """
    计算下次运行时间（ISO 8601 字符串）

    Args:
        schedule_type: 'interval' | 'cron'
        schedule_config: 调度配置
        last_run_time: 上次成功运行时间，None 表示从未运行
        created_at: 创建时间
        now: 当前时间，None 则用 UTC

    Returns:
        ISO 8601 格式的下次运行时间
    """
    if now is None:
        now = utc_now()

    if schedule_type == "interval":
        return _compute_interval_next(
            schedule_config=schedule_config,
            last_run_time=last_run_time,
            created_at=created_at,
            now=now,
        )
    if schedule_type == "cron":
        return _compute_cron_next(
            schedule_config=schedule_config,
            now=now,
        )
    raise ValueError(f"不支持的 schedule_type: {schedule_type}")


def _compute_interval_next(
    schedule_config: dict,
    last_run_time: Optional[str],
    created_at: str,
    now: datetime,
) -> str:
    """interval 类型：首次立即执行，之后按 interval_seconds 间隔"""
    if last_run_time is None:
        # 首次：立即执行（返回当前时间，使 next_run_time <= now 即可被心跳拉取）
        return now.isoformat()
    anchor_str = last_run_time
    anchor = datetime.fromisoformat(anchor_str.replace("Z", "+00:00"))
    # 兼容 naive datetime
    if anchor.tzinfo is None and now.tzinfo is not None:
        anchor = anchor.replace(tzinfo=now.tzinfo)
    elif anchor.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=anchor.tzinfo)

    interval_sec = schedule_config.get("interval_seconds", 3600)
    next_dt = anchor + timedelta(seconds=interval_sec)

    # 若已过下次时间（如服务重启导致错过），从 now 起算下一个周期
    if next_dt <= now:
        elapsed = (now - anchor).total_seconds()
        periods = int(elapsed / interval_sec) + 1
        next_dt = anchor + timedelta(seconds=periods * interval_sec)

    return next_dt.isoformat()


def _compute_cron_next(
    schedule_config: dict,
    now: datetime,
) -> str:
    """cron 类型：使用 croniter 计算下次运行时间"""
    try:
        from croniter import croniter
    except ImportError:
        raise RuntimeError("cron 解析需要安装 croniter: pip install croniter")

    cron_expr = schedule_config.get("cron", "").strip()
    if not cron_expr:
        raise ValueError("cron 类型需要 schedule_config.cron 非空")

    tz_str = schedule_config.get("tz")
    if tz_str:
        try:
            from zoneinfo import ZoneInfo
            now = now.astimezone(ZoneInfo(tz_str))
        except Exception:
            pass  # 无效时区则用本地时间

    it = croniter(cron_expr, now)
    next_dt = it.get_next(datetime)
    return next_dt.isoformat()
