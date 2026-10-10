"""Baserow 数据看板接口(多数据源 + 按部门过滤 + 权限控制)。"""

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.permissions import management_scope
from app.db.session import get_db
from app.models.user import User
from app.services import baserow
from app.services.baserow import BaserowError, BaserowSource

router = APIRouter(prefix="/data", tags=["数据看板"])


def _is_global(user: User) -> bool:
    return management_scope(user) == "all"


def _source_for(table_id: str) -> BaserowSource:
    source = baserow.source_for_table(table_id)
    if source is None:
        raise HTTPException(status_code=404, detail="未知数据集")
    return source


def _dept_filter(source: BaserowSource, table_id: str, user: User) -> Optional[dict[str, str]]:
    """构造按部门过滤的 Baserow 参数;返回 None 表示强制空结果。"""
    field = source.department_field
    if not field or _is_global(user):
        return {}
    if not user.department:
        return None

    try:
        fields = baserow.list_fields(source, table_id)
    except BaserowError:
        return None
    fdef = next((f for f in fields if f.get("name") == field), None)
    if fdef is None:
        return {}
    ftype = fdef.get("type")
    if ftype in ("single_select", "multiple_select"):
        options = fdef.get("select_options") or []
        option = next((o for o in options if o.get("value") == user.department), None)
        if option is None:
            return None
        op = "single_select_equal" if ftype == "single_select" else "multiple_select_has"
        return {f"filter__{field}__{op}": str(option["id"])}
    return {f"filter__{field}__equal": user.department}


def _row_dept_value(source: BaserowSource, row: dict[str, Any]) -> Optional[str]:
    field = source.department_field
    if not field:
        return None
    value = row.get(field)
    if isinstance(value, dict):
        return value.get("value")
    return value


def _assert_row_scope(source: BaserowSource, table_id: str, row_id: int, user: User) -> None:
    if not source.department_field or _is_global(user):
        return
    try:
        row = baserow.get_row(source, table_id, row_id)
    except BaserowError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if _row_dept_value(source, row) != user.department:
        raise HTTPException(status_code=403, detail="只能操作本部门数据")


@router.get("/datasets", summary="数据集列表(跨数据源)")
def datasets(_: User = Depends(require_permission("data:view"))) -> list[dict[str, str]]:
    return baserow.all_datasets()


@router.get("/tables/{table_id}/fields", summary="数据表字段")
def table_fields(
    table_id: str,
    _: User = Depends(require_permission("data:view")),
) -> list[dict[str, Any]]:
    source = _source_for(table_id)
    try:
        return baserow.list_fields(source, table_id)
    except BaserowError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/tables/{table_id}/rows", summary="数据行")
def table_rows(
    table_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:view")),
) -> dict[str, Any]:
    source = _source_for(table_id)
    dept_filter = _dept_filter(source, table_id, current)
    if dept_filter is None:
        return {"count": 0, "next": None, "previous": None, "results": []}
    try:
        return baserow.list_rows(
            source, table_id, page=page, size=size, search=search, filters=dept_filter
        )
    except BaserowError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/tables/{table_id}/rows", summary="新增数据行")
def create_row(
    table_id: str,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:create")),
) -> dict[str, Any]:
    source = _source_for(table_id)
    body = dict(payload)
    if source.department_field and not _is_global(current) and current.department:
        body[source.department_field] = current.department
    try:
        return baserow.create_row(source, table_id, body)
    except BaserowError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.patch("/tables/{table_id}/rows/{row_id}", summary="更新数据行")
def update_row(
    table_id: str,
    row_id: int,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:edit")),
) -> dict[str, Any]:
    source = _source_for(table_id)
    _assert_row_scope(source, table_id, row_id, current)
    try:
        return baserow.update_row(source, table_id, row_id, payload)
    except BaserowError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.delete("/tables/{table_id}/rows/{row_id}", summary="删除数据行")
def delete_row(
    table_id: str,
    row_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("data:delete")),
) -> dict[str, bool]:
    source = _source_for(table_id)
    _assert_row_scope(source, table_id, row_id, current)
    try:
        baserow.delete_row(source, table_id, row_id)
    except BaserowError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"ok": True}
