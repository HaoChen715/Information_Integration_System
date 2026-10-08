from __future__ import annotations

from typing import Optional, Union

from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import user as user_crud
from app.models.user import User
from app.services.auth.base import AuthError, AuthIdentity
from app.services.auth.ldap import LdapAuthProvider
from app.services.auth.local import LocalAuthProvider

__all__ = ["authenticate", "AuthError", "AuthIdentity"]

# 认证后端注册表:key 与 settings.AUTH_BACKENDS 对应
_PROVIDERS = {
    "local": LocalAuthProvider(),
    "ldap": LdapAuthProvider(),
}


def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    """按配置顺序尝试各认证后端,返回本地 User 对象或 None。"""
    for backend in settings.AUTH_BACKENDS:
        provider = _PROVIDERS.get(backend)
        if provider is None:
            continue

        result: Union[User, AuthIdentity, None] = provider.authenticate(db, username, password)
        if result is None:
            continue

        if isinstance(result, User):
            return result

        # AD 身份 -> JIT 开通并同步角色
        if not settings.LDAP_AUTO_PROVISION:
            raise AuthError("账号未开通,请联系管理员", 403)
        return user_crud.upsert_ad_user(db, result, settings.LDAP_GROUP_ROLE_MAP)

    return None
