"""部门空间接口(任意登录用户可访问自己的部门)。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.avatars import avatar_url
from app.core.presence import is_online
from app.db.session import get_db
from app.models.department import Department
from app.models.user import User
from app.schemas.rbac import DepartmentMemberOut, DepartmentOut

router = APIRouter(prefix="/departments", tags=["部门"])


@router.get("/options", response_model=list[DepartmentOut], summary="部门选项")
def department_options(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DepartmentOut]:
    rows = list(db.execute(select(Department).order_by(Department.name)).scalars())
    return [DepartmentOut.model_validate(d) for d in rows]


@router.get(
    "/me/members",
    response_model=list[DepartmentMemberOut],
    summary="我所在部门的成员",
)
def my_department_members(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[DepartmentMemberOut]:
    if not current.department:
        return []
    rows = list(
        db.execute(
            select(User).where(User.department == current.department).order_by(User.id)
        ).scalars()
    )
    return [
        DepartmentMemberOut(
            id=u.id,
            username=u.username,
            full_name=u.full_name,
            department=u.department,
            avatar_url=avatar_url(u),
            roles=u.role_codes,
            role_names=[role.name for role in u.roles],
            is_active=u.is_active,
            is_online=is_online(u.last_seen_at),
            last_login_at=u.last_login_at,
            last_seen_at=u.last_seen_at,
        )
        for u in rows
    ]
