from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.crud import user as user_crud
from app.models.user import User


class LocalAuthProvider:
    """本地账号认证:bcrypt 校验密码。"""

    name = "local"

    def authenticate(self, db: Session, username: str, password: str) -> Optional[User]:
        user = user_crud.get_by_username(db, username)
        # 仅处理本地来源账号;AD 账号没有本地密码
        if user is None or user.auth_source != "local" or not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
