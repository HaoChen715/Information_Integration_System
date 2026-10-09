from datetime import datetime, timezone
from typing import Annotated

from pydantic import BeforeValidator


def _ensure_utc(value: object) -> object:
    """SQLite 等不保存时区,读出的 naive 时间按 UTC 处理,补上时区标识。"""
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# 输出带时区的时间,前端 new Date() 可正确换算本地时间
UTCDatetime = Annotated[datetime, BeforeValidator(_ensure_utc)]
