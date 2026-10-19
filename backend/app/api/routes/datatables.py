"""原生数据表:记录读写(按数据范围过滤)。"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.routes.datatables_admin import table_out
from app.core.permissions import effective_permissions, management_scope
from app.crud import data_table as crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.data_table import RecordCreate, RecordOut, RecordUpdate, TableOut

router = APIRouter(prefix="/datatables", tags=["数据表"])


def _is_global(user: User) -> bool:
    return management_scope(user) == "all"


def _scope_of(db: Session, user: User, code: str) -> Optional[str]:
    if _is_global(user):
        return "all"
    return effective_permissions(db, user).get(code)


def _table_or_404(db: Session, code: str):
    table = crud.get_table_by_code(db, code)
    if table is None:
        raise HTTPException(status_code=404, detail="数据表不存在")
    return table


def _check_record_access(
    db: Session, table, record, user: User, perm_code: str, is_global: bool
) -> None:
    scope = _scope_of(db, user, perm_code)
    if scope is None:
        raise HTTPException(status_code=403, detail="无权限")
    if not crud.record_visible(table, record, user, scope, is_global):
        raise HTTPException(status_code=403, detail="只能操作本范围内的数据")


@router.get("", response_model=list[TableOut], summary="可访问的数据表")
def list_tables(
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:view")),
) -> list[TableOut]:
    return [table_out(t) for t in crud.list_tables(db)]


@router.get("/{code}/records", response_model=list[RecordOut], summary="记录列表")
def list_records(
    code: str,
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:view")),
) -> list[RecordOut]:
    table = _table_or_404(db, code)
    scope = _scope_of(db, current, "data:view") or "self"
    records = crud.list_records(db, table, current, scope, _is_global(current), search)
    return [
        RecordOut(
            id=r.id,
            data=r.data or {},
            owner_username=r.owner_username,
            department=r.department,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]


@router.post("/{code}/records", response_model=RecordOut, summary="新增记录")
def create_record(
    code: str,
    payload: RecordCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:create")),
) -> RecordOut:
    table = _table_or_404(db, code)
    record = crud.create_record(db, table, current, dict(payload.data))
    return RecordOut(
        id=record.id,
        data=record.data or {},
        owner_username=record.owner_username,
        department=record.department,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.put("/{code}/records/{record_id}", response_model=RecordOut, summary="更新记录")
def update_record(
    code: str,
    record_id: int,
    payload: RecordUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:edit")),
) -> RecordOut:
    table = _table_or_404(db, code)
    record = crud.get_record(db, table, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    _check_record_access(db, table, record, current, "data:edit", _is_global(current))
    record = crud.update_record(db, record, dict(payload.data))
    return RecordOut(
        id=record.id,
        data=record.data or {},
        owner_username=record.owner_username,
        department=record.department,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.delete("/{code}/records/{record_id}", summary="删除记录")
def delete_record(
    code: str,
    record_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:delete")),
) -> dict[str, bool]:
    table = _table_or_404(db, code)
    record = crud.get_record(db, table, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    _check_record_access(db, table, record, current, "data:delete", _is_global(current))
    crud.delete_record(db, record)
    return {"ok": True}


@router.get("/{code}/stats", summary="记录统计(按字段分组)")
def record_stats(
    code: str,
    group_by: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:view")),
) -> dict[str, Any]:
    table = _table_or_404(db, code)
    scope = _scope_of(db, current, "data:view") or "self"
    records = crud.list_records(db, table, current, scope, _is_global(current))
    counts: dict[str, int] = {}
    for r in records:
        val = (r.data or {}).get(group_by)
        label = str(val) if val not in (None, "") else "（空）"
        counts[label] = counts.get(label, 0) + 1
    return {
        "total": len(records),
        "groups": sorted(
            [{"label": k, "count": v} for k, v in counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        ),
    }
