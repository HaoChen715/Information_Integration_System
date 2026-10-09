"""权限目录与有效权限计算。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import Permission, RolePermission, UserPermission
from app.models.role import Role
from app.models.user import User

# 数据范围:all(全部) > dept(本部门) > self(仅本人)
DATA_SCOPES = ("self", "dept", "all")
SCOPE_RANK = {"self": 1, "dept": 2, "all": 3}

# 资源分组标签
RESOURCE_LABELS = {
    "dashboard": "主页",
    "user": "用户管理",
    "role": "角色管理",
    "record": "资料数据",
}

# 权限目录:(code, 名称, 资源, 操作)
PERMISSION_CATALOG = [
    ("dashboard:view", "查看主页", "dashboard", "view"),
    ("user:view", "查看用户", "user", "view"),
    ("user:create", "新增用户", "user", "create"),
    ("user:edit", "编辑用户", "user", "edit"),
    ("user:delete", "删除用户", "user", "delete"),
    ("role:view", "查看角色", "role", "view"),
    ("role:create", "新增角色", "role", "create"),
    ("role:edit", "编辑角色", "role", "edit"),
    ("role:delete", "删除角色", "role", "delete"),
    ("record:view", "查看资料", "record", "view"),
    ("record:create", "新增资料", "record", "create"),
    ("record:edit", "编辑资料", "record", "edit"),
    ("record:delete", "删除资料", "record", "delete"),
]


def seed_permissions(db: Session) -> None:
    """按目录幂等地写入权限点。"""
    existing = {
        code for (code,) in db.execute(select(Permission.code)).all()
    }
    for code, name, resource, action in PERMISSION_CATALOG:
        if code in existing:
            continue
        db.add(Permission(code=code, name=name, resource=resource, action=action))
    db.commit()


def seed_default_roles(db: Session) -> None:
    """内置角色:管理员角色(拥有全部权限,is_admin)。"""
    role = db.execute(select(Role).where(Role.code == "admin")).scalar_one_or_none()
    if role is None:
        role = Role(
            code="admin",
            name="管理员",
            description="系统内置管理员角色,拥有全部权限",
            is_system=True,
            is_admin=True,
        )
        db.add(role)
        db.flush()
    else:
        role.is_system = True
        role.is_admin = True
        if not role.name:
            role.name = "管理员"
    existing = {
        pid
        for (pid,) in db.execute(
            select(RolePermission.permission_id).where(RolePermission.role_id == role.id)
        ).all()
    }
    for perm in db.execute(select(Permission)).scalars():
        if perm.id not in existing:
            db.add(
                RolePermission(role_id=role.id, permission_id=perm.id, data_scope="all")
            )
    db.commit()


def _max_scope(current: Optional[str], new: str) -> str:
    if current is None:
        return new
    return current if SCOPE_RANK.get(current, 0) >= SCOPE_RANK.get(new, 0) else new


def effective_permissions(db: Session, user: User) -> dict[str, str]:
    """返回用户的有效权限:{权限code: 数据范围}。超级管理员拥有全部(all)。"""
    if user.is_superuser:
        codes = db.execute(select(Permission.code)).scalars().all()
        return {code: "all" for code in codes}

    result: dict[str, str] = {}

    role_ids = [role.id for role in user.roles]
    if role_ids:
        rows = db.execute(
            select(Permission.code, RolePermission.data_scope)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(role_ids))
        ).all()
        for code, scope in rows:
            result[code] = _max_scope(result.get(code), scope)

    rows = db.execute(
        select(Permission.code, UserPermission.data_scope)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user.id)
    ).all()
    for code, scope in rows:
        result[code] = _max_scope(result.get(code), scope)

    return result


def is_admin(user: User) -> bool:
    """超级管理员或任意管理员角色。"""
    return user.is_superuser or any(role.is_admin for role in user.roles)
