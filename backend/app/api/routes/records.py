"""演示数据范围的示例数据接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.permissions import effective_permissions
from app.db.session import get_db
from app.models.record import DemoRecord
from app.models.user import User
from app.schemas.record import RecordCreate, RecordOut

router = APIRouter(prefix="/records", tags=["资料(演示数据范围)"])


def _scope_for(db: Session, user: User, code: str) -> str:
    if user.is_superuser:
        return "all"
    return effective_permissions(db, user).get(code, "self")


@router.get("", response_model=list[RecordOut], summary="资料列表(按数据范围过滤)")
def list_records(
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("record:view")),
) -> list[DemoRecord]:
    scope = _scope_for(db, current, "record:view")
    stmt = select(DemoRecord)
    if scope == "self":
        stmt = stmt.where(DemoRecord.owner_username == current.username)
    elif scope == "dept":
        if current.department:
            stmt = stmt.where(DemoRecord.department == current.department)
        else:
            stmt = stmt.where(DemoRecord.owner_username == current.username)
    return list(db.execute(stmt.order_by(DemoRecord.id)).scalars())


@router.post("", response_model=RecordOut, summary="新增资料")
def create_record(
    payload: RecordCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("record:create")),
) -> DemoRecord:
    record = DemoRecord(
        title=payload.title,
        content=payload.content,
        owner_username=current.username,
        department=current.department,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
