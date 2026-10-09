from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_superuser
from app.core.config import settings
from app.core.permissions import RESOURCE_LABELS, effective_permissions
from app.crud import rbac as rbac_crud
from app.db.session import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.rbac import (
    PermissionGroup,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserAdminOut,
    UserPermissionsUpdate,
    UserRolesUpdate,
    UserUpdate,
)

router = APIRouter(prefix="/admin", tags=["权限管理"])


def _role_out(db: Session, role: Role) -> RoleOut:
    return RoleOut(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        is_admin=role.is_admin,
        permissions=rbac_crud.role_grants(db, role),
    )


def _user_out(db: Session, user: User) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        auth_source=user.auth_source,
        roles=user.role_codes,
        permissions=effective_permissions(db, user),
        direct_permissions=rbac_crud.user_grants(db, user),
    )


# ---------------- 权限目录 ----------------
@router.get("/permissions", response_model=list[PermissionGroup], summary="权限目录")
def list_permissions(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[PermissionGroup]:
    rows = list(
        db.execute(
            select(Permission).order_by(Permission.resource, Permission.action)
        ).scalars()
    )
    grouped: dict[str, list[PermissionOut]] = {}
    for perm in rows:
        grouped.setdefault(perm.resource, []).append(PermissionOut.model_validate(perm))
    return [
        PermissionGroup(
            resource=resource,
            label=RESOURCE_LABELS.get(resource, resource),
            permissions=perms,
        )
        for resource, perms in grouped.items()
    ]


# ---------------- 角色管理 ----------------
@router.get("/roles", response_model=list[RoleOut], summary="角色列表")
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[RoleOut]:
    return [_role_out(db, role) for role in rbac_crud.list_roles(db)]


@router.post("/roles", response_model=RoleOut, summary="新增角色")
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_admin),
) -> RoleOut:
    if payload.is_admin and not current.is_superuser:
        raise HTTPException(status_code=403, detail="仅超级管理员可创建管理员角色")
    try:
        role = rbac_crud.create_role(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _role_out(db, role)


@router.put("/roles/{role_id}", response_model=RoleOut, summary="更新角色")
def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_admin),
) -> RoleOut:
    role = rbac_crud.get_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if (role.is_admin or payload.is_admin) and not current.is_superuser:
        raise HTTPException(status_code=403, detail="仅超级管理员可修改管理员角色")
    try:
        role = rbac_crud.update_role(db, role, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _role_out(db, role)


@router.delete("/roles/{role_id}", summary="删除角色")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_admin),
) -> dict:
    role = rbac_crud.get_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可删除")
    if role.is_admin and not current.is_superuser:
        raise HTTPException(status_code=403, detail="仅超级管理员可删除管理员角色")
    rbac_crud.delete_role(db, role)
    return {"ok": True}


# ---------------- 用户与授权 ----------------
@router.get("/stats", summary="用户统计")
def user_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    total = db.execute(select(func.count()).select_from(User)).scalar_one()
    active = db.execute(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ).scalar_one()
    # last_seen_at 以 naive UTC 存储
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=settings.ONLINE_WINDOW_MINUTES
    )
    online = db.execute(
        select(func.count()).select_from(User).where(User.last_seen_at >= cutoff)
    ).scalar_one()
    by_source = {
        source: count
        for source, count in db.execute(
            select(User.auth_source, func.count()).group_by(User.auth_source)
        ).all()
    }
    return {
        "total_users": total,
        "active_users": active,
        "online_users": online,
        "by_source": by_source,
        "online_window_minutes": settings.ONLINE_WINDOW_MINUTES,
    }


@router.get("/users", response_model=list[UserAdminOut], summary="用户列表")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[UserAdminOut]:
    return [_user_out(db, user) for user in rbac_crud.list_users(db)]


@router.put("/users/{user_id}", response_model=UserAdminOut, summary="更新用户信息")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> UserAdminOut:
    user = rbac_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.department is not None:
        user.department = payload.department
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.put("/users/{user_id}/roles", response_model=UserAdminOut, summary="分配角色")
def assign_roles(
    user_id: int,
    payload: UserRolesUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_admin),
) -> UserAdminOut:
    user = rbac_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    target_roles = list(
        db.execute(select(Role).where(Role.code.in_(payload.roles))).scalars()
    )
    if any(role.is_admin for role in target_roles) and not current.is_superuser:
        raise HTTPException(status_code=403, detail="仅超级管理员可授予管理员角色")

    try:
        rbac_crud.assign_user_roles(db, user, payload.roles)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.refresh(user)
    return _user_out(db, user)


@router.put(
    "/users/{user_id}/permissions",
    response_model=UserAdminOut,
    summary="直接给用户赋权",
)
def set_user_permissions(
    user_id: int,
    payload: UserPermissionsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> UserAdminOut:
    user = rbac_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    try:
        rbac_crud.replace_user_permissions(db, user, payload.permissions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.refresh(user)
    return _user_out(db, user)


@router.put(
    "/users/{user_id}/superuser",
    response_model=UserAdminOut,
    summary="授予/撤销超级管理员(仅超管)",
)
def set_superuser(
    user_id: int,
    value: bool,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_superuser),
) -> UserAdminOut:
    user = rbac_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current.id and not value:
        raise HTTPException(status_code=400, detail="不能撤销自己的超级管理员权限")
    user.is_superuser = value
    db.commit()
    db.refresh(user)
    return _user_out(db, user)
