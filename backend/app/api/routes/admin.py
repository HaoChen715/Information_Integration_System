from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_admin,
    get_current_manager,
    get_current_superuser,
)
from app.core.avatars import avatar_url
from app.core.config import settings
from app.core.permissions import (
    RESOURCE_LABELS,
    effective_permissions,
    is_department_manager,
    management_scope,
)
from app.crud import rbac as rbac_crud
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.department import Department
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.rbac import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    OnlineUserOut,
    PermissionGroup,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserAdminOut,
    UserCreateAdmin,
    UserPermissionsUpdate,
    UserRolesUpdate,
    UserUpdate,
)
from app.schemas.user import UserCreate

router = APIRouter(prefix="/admin", tags=["权限管理"])

# 部门主管不可授予的权限资源(用户/角色管理属于管理类权限)
_MANAGEMENT_RESOURCES = {"user", "role"}


def _role_out(db: Session, role: Role) -> RoleOut:
    return RoleOut(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        is_admin=role.is_admin,
        is_department_manager=role.is_department_manager,
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
        avatar_url=avatar_url(user),
    )


def _assert_can_manage(current: User, target: User) -> str:
    """校验当前用户能否管理目标用户,返回管理范围。"""
    scope = management_scope(current)
    if scope is None:
        raise HTTPException(status_code=403, detail="需要管理员或主管权限")
    if scope == "all":
        return scope
    # 部门主管:仅能管理本部门、且非管理员/非主管的普通员工
    if target.department != current.department:
        raise HTTPException(status_code=403, detail="只能管理本部门员工")
    if target.is_superuser or rbac_crud_is_admin(target) or is_department_manager(target):
        raise HTTPException(status_code=403, detail="无权管理管理员或主管账号")
    return scope


def rbac_crud_is_admin(user: User) -> bool:
    return user.is_superuser or any(role.is_admin for role in user.roles)


# ---------------- 权限目录 ----------------
@router.get("/permissions", response_model=list[PermissionGroup], summary="权限目录")
def list_permissions(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_manager),
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


# ---------------- 部门管理 ----------------
@router.get("/departments", response_model=list[DepartmentOut], summary="部门列表")
def list_departments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_manager),
) -> list[Department]:
    return list(db.execute(select(Department).order_by(Department.id)).scalars())


@router.post("/departments", response_model=DepartmentOut, summary="新增部门")
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> Department:
    if db.execute(select(Department).where(Department.name == payload.name)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="部门已存在")
    dept = Department(name=payload.name, description=payload.description)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.put("/departments/{dept_id}", response_model=DepartmentOut, summary="更新部门")
def update_department(
    dept_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> Department:
    dept = db.get(Department, dept_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    if payload.name and payload.name != dept.name:
        if db.execute(select(Department).where(Department.name == payload.name)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="部门已存在")
        # 同步更新用户上的部门名
        old = dept.name
        for user in db.execute(select(User).where(User.department == old)).scalars():
            user.department = payload.name
        dept.name = payload.name
    if payload.description is not None:
        dept.description = payload.description
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/departments/{dept_id}", summary="删除部门")
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    dept = db.get(Department, dept_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    db.delete(dept)
    db.commit()
    return {"ok": True}


# ---------------- 角色管理 ----------------
@router.get("/roles", response_model=list[RoleOut], summary="角色列表")
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_manager),
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


@router.get("/online-users", response_model=list[OnlineUserOut], summary="当前在线用户")
def online_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[OnlineUserOut]:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=settings.ONLINE_WINDOW_MINUTES
    )
    rows = list(
        db.execute(
            select(User).where(User.last_seen_at >= cutoff).order_by(User.last_seen_at.desc())
        ).scalars()
    )
    return [
        OnlineUserOut(
            id=u.id,
            username=u.username,
            full_name=u.full_name,
            department=u.department,
            email=u.email,
            auth_source=u.auth_source,
            roles=u.role_codes,
            last_login_at=u.last_login_at,
            last_seen_at=u.last_seen_at,
            avatar_url=avatar_url(u),
        )
        for u in rows
    ]


@router.get("/users", response_model=list[UserAdminOut], summary="用户列表")
def list_users(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_manager),
) -> list[UserAdminOut]:
    scope = management_scope(current)
    stmt = select(User).order_by(User.id)
    if scope == "dept":
        stmt = stmt.where(User.department == current.department)
    return [_user_out(db, u) for u in db.execute(stmt).scalars()]


@router.post("/users", response_model=UserAdminOut, summary="新增用户")
def create_user_route(
    payload: UserCreateAdmin,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_manager),
) -> UserAdminOut:
    scope = management_scope(current)
    if user_crud.get_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="用户名已存在")

    department = payload.department
    if scope == "dept":
        department = current.department  # 主管只能在本部门新增

    target_roles = list(
        db.execute(select(Role).where(Role.code.in_(payload.roles))).scalars()
    )
    for role in target_roles:
        if role.is_admin and not current.is_superuser:
            raise HTTPException(status_code=403, detail="仅超级管理员可授予管理员角色")
        if scope == "dept" and role.is_department_manager:
            raise HTTPException(status_code=403, detail="主管不能授予主管角色")

    try:
        user = user_crud.create_user(
            db,
            UserCreate(
                username=payload.username,
                password=payload.password,
                email=payload.email,
                full_name=payload.full_name,
            ),
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="用户名或邮箱已被占用")

    user.department = department
    user.is_active = payload.is_active
    db.commit()
    rbac_crud.assign_user_roles(db, user, payload.roles)
    db.refresh(user)
    return _user_out(db, user)


@router.delete("/users/{user_id}", summary="删除用户")
def delete_user_route(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_manager),
) -> dict:
    user = rbac_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    _assert_can_manage(current, user)
    if user.is_superuser or (rbac_crud_is_admin(user) and not current.is_superuser):
        raise HTTPException(status_code=403, detail="无权删除该账号")
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.put("/users/{user_id}", response_model=UserAdminOut, summary="更新用户信息")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_manager),
) -> UserAdminOut:
    user = rbac_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    scope = _assert_can_manage(current, user)

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.department is not None:
        if scope == "dept" and payload.department != current.department:
            raise HTTPException(status_code=403, detail="主管不能修改部门归属")
        user.department = payload.department
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.put("/users/{user_id}/roles", response_model=UserAdminOut, summary="分配角色")
def assign_roles(
    user_id: int,
    payload: UserRolesUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_manager),
) -> UserAdminOut:
    user = rbac_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    scope = _assert_can_manage(current, user)

    target_roles = list(
        db.execute(select(Role).where(Role.code.in_(payload.roles))).scalars()
    )
    for role in target_roles:
        if role.is_admin and not current.is_superuser:
            raise HTTPException(status_code=403, detail="仅超级管理员可授予管理员角色")
        if scope == "dept" and role.is_department_manager:
            raise HTTPException(status_code=403, detail="主管不能授予主管角色")
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
    current: User = Depends(get_current_manager),
) -> UserAdminOut:
    user = rbac_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    scope = _assert_can_manage(current, user)

    grants = list(payload.permissions)
    if scope == "dept":
        # 部门主管:保留已有的管理类权限,忽略其试图新增的管理类权限
        kept = []
        for grant in rbac_crud.user_grants(db, user):
            perm = rbac_crud.get_permission_by_code(db, grant.code)
            if perm is not None and perm.resource in _MANAGEMENT_RESOURCES:
                kept.append(grant)
        filtered = []
        for grant in grants:
            perm = rbac_crud.get_permission_by_code(db, grant.code)
            if perm is not None and perm.resource in _MANAGEMENT_RESOURCES:
                continue
            filtered.append(grant)
        grants = kept + filtered

    try:
        rbac_crud.replace_user_permissions(db, user, grants)
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
