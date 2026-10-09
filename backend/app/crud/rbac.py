from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.permission import Permission, RolePermission, UserPermission
from app.models.role import Role
from app.models.user import User
from app.schemas.rbac import PermissionGrant, RoleCreate, RoleUpdate


def list_roles(db: Session) -> list[Role]:
    return list(db.execute(select(Role).order_by(Role.id)).scalars())


def get_role(db: Session, role_id: int) -> Optional[Role]:
    return db.get(Role, role_id)


def get_role_by_code(db: Session, code: str) -> Optional[Role]:
    return db.execute(select(Role).where(Role.code == code)).scalar_one_or_none()


def get_permission_by_code(db: Session, code: str) -> Optional[Permission]:
    return db.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none()


def _replace_role_permissions(db: Session, role: Role, grants: list[PermissionGrant]) -> None:
    db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    for grant in grants:
        perm = get_permission_by_code(db, grant.code)
        if perm is None:
            raise ValueError(f"未知权限:{grant.code}")
        db.add(
            RolePermission(
                role_id=role.id, permission_id=perm.id, data_scope=grant.data_scope
            )
        )


def role_grants(db: Session, role: Role) -> list[PermissionGrant]:
    rows = db.execute(
        select(Permission.code, RolePermission.data_scope)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
    ).all()
    return [PermissionGrant(code=code, data_scope=scope) for code, scope in rows]


def create_role(db: Session, data: RoleCreate) -> Role:
    if get_role_by_code(db, data.code):
        raise ValueError(f"角色 code 已存在:{data.code}")
    role = Role(
        code=data.code,
        name=data.name,
        description=data.description,
        is_admin=data.is_admin,
        is_department_manager=data.is_department_manager,
    )
    db.add(role)
    db.flush()
    _replace_role_permissions(db, role, data.permissions)
    db.commit()
    db.refresh(role)
    return role


def update_role(db: Session, role: Role, data: RoleUpdate) -> Role:
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.is_admin is not None:
        role.is_admin = data.is_admin
    if data.is_department_manager is not None:
        role.is_department_manager = data.is_department_manager
    if data.permissions is not None:
        _replace_role_permissions(db, role, data.permissions)
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role: Role) -> None:
    db.delete(role)
    db.commit()


def assign_user_roles(db: Session, user: User, role_codes: list[str]) -> None:
    roles = list(db.execute(select(Role).where(Role.code.in_(role_codes))).scalars())
    found = {role.code for role in roles}
    missing = set(role_codes) - found
    if missing:
        raise ValueError(f"未知角色:{', '.join(sorted(missing))}")
    user.roles = roles
    db.commit()


def user_grants(db: Session, user: User) -> list[PermissionGrant]:
    rows = db.execute(
        select(Permission.code, UserPermission.data_scope)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user.id)
    ).all()
    return [PermissionGrant(code=code, data_scope=scope) for code, scope in rows]


def replace_user_permissions(
    db: Session, user: User, grants: list[PermissionGrant]
) -> None:
    db.execute(delete(UserPermission).where(UserPermission.user_id == user.id))
    for grant in grants:
        perm = get_permission_by_code(db, grant.code)
        if perm is None:
            raise ValueError(f"未知权限:{grant.code}")
        db.add(
            UserPermission(
                user_id=user.id, permission_id=perm.id, data_scope=grant.data_scope
            )
        )
    db.commit()


def list_users(db: Session) -> list[User]:
    return list(db.execute(select(User).order_by(User.id)).scalars())


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)
