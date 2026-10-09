from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import effective_permissions, is_admin, management_scope
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="登录凭证无效或已过期",
    headers={"WWW-Authenticate": "Bearer"},
)


def _touch_last_seen(db: Session, user: User) -> None:
    """按最小间隔更新用户活跃时间(用于在线统计)。"""
    now = datetime.now(timezone.utc)
    seen = user.last_seen_at
    if seen is not None and seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    if seen is None or (now - seen).total_seconds() >= settings.LAST_SEEN_UPDATE_SECONDS:
        user.last_seen_at = now
        db.add(user)
        db.commit()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = user_crud.get_by_username(db, username)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    _touch_last_seen(db, user)
    return user


def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限")
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """超级管理员或管理员角色。"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user


def get_current_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    """全局管理员或部门主管。"""
    if management_scope(current_user) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员或主管权限")
    return current_user


def require_permission(code: str):
    """依赖工厂:要求当前用户拥有指定权限点。"""

    def checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user
        if code not in effective_permissions(db, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该资源"
            )
        return current_user

    return checker
