from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth.base import AuthError, AuthIdentity


def get_by_username(db: Session, username: str) -> Optional[User]:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def create_user(db: Session, data: UserCreate, *, is_superuser: bool = False) -> User:
    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_role(db: Session, code: str, name: Optional[str] = None) -> Role:
    role = db.execute(select(Role).where(Role.code == code)).scalar_one_or_none()
    if role is None:
        role = Role(code=code, name=name or code)
        db.add(role)
        db.flush()
    return role


def ensure_bootstrap_admin(db: Session) -> None:
    """首次启动时按配置创建引导管理员(已存在则跳过)。"""
    username = settings.BOOTSTRAP_ADMIN_USERNAME
    password = settings.BOOTSTRAP_ADMIN_PASSWORD
    if not username or not password:
        return
    if get_by_username(db, username):
        return
    create_user(
        db,
        UserCreate(
            username=username,
            password=password,
            email=settings.BOOTSTRAP_ADMIN_EMAIL,
        ),
        is_superuser=True,
    )


def _group_keys(groups: list[str]) -> set[str]:
    """把组 DN 归一化为可比较的标识(完整 DN + CN,均小写)。"""
    keys: set[str] = set()
    for group in groups:
        keys.add(group.lower())
        if group.lower().startswith("cn="):
            keys.add(group.split(",", 1)[0][3:].lower())
    return keys


def match_roles(groups: list[str], group_role_map: dict[str, str]) -> list[str]:
    """根据 AD 组映射出本地角色 code 列表。"""
    keys = _group_keys(groups)
    return [code for group, code in group_role_map.items() if group.lower() in keys]


def upsert_ad_user(
    db: Session,
    identity: AuthIdentity,
    group_role_map: dict[str, str],
) -> User:
    """AD 用户 JIT 开通 / 信息与角色同步。"""
    user = get_by_username(db, identity.username)
    if user is None:
        user = User(
            username=identity.username,
            auth_source="ad",
            hashed_password="",  # AD 账号不使用本地密码
            is_active=True,
        )
        db.add(user)
    elif user.auth_source != "ad":
        raise AuthError("该账号已存在且为本地账号,请联系管理员", 409)

    user.email = identity.email or user.email
    user.full_name = identity.full_name or user.full_name

    role_codes = match_roles(identity.groups, group_role_map)
    user.roles = [get_or_create_role(db, code) for code in role_codes]

    db.commit()
    db.refresh(user)
    return user
