"""头像存储辅助。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.models.user import User

# content-type -> 扩展名
ALLOWED_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}
EXT_MEDIA_TYPE = {v: k for k, v in ALLOWED_TYPES.items()}


def avatar_dir() -> Path:
    path = Path(settings.AVATAR_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def avatar_url(user: User) -> Optional[str]:
    if not user.avatar_ext:
        return None
    ts = user.avatar_updated_at
    version = int(ts.timestamp()) if ts else 0
    return f"{settings.API_V1_PREFIX}/users/{user.id}/avatar?v={version}"
