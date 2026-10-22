"""用户在线状态判定。"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings


def is_online(last_seen: Optional[datetime], now: Optional[datetime] = None) -> bool:
    """最近活跃时间在在线窗口内视为在线。"""
    if last_seen is None:
        return False
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    ref = now or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return ref - last_seen <= timedelta(minutes=settings.ONLINE_WINDOW_MINUTES)
