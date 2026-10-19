"""原生数据表定义(管理员)。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.crud import data_table as crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.data_table import FieldOut, TableCreate, TableOut, TableUpdate

router = APIRouter(prefix="/admin/datatables", tags=["数据表定义"])


def table_out(table) -> TableOut:
    return TableOut(
        id=table.id,
        code=table.code,
        name=table.name,
        description=table.description,
        title_field=table.title_field,
        scope_by_department=table.scope_by_department,
        department_field=table.department_field or "",
        fields=[
            FieldOut(
                id=f.id,
                key=f.key,
                label=f.label,
                type=f.type,
                required=f.required,
                options=f.options or [],
            )
            for f in table.fields
        ],
    )


@router.get("", response_model=list[TableOut], summary="数据表列表")
def list_tables(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[TableOut]:
    return [table_out(t) for t in crud.list_tables(db)]


@router.post("", response_model=TableOut, summary="新建数据表")
def create_table(
    payload: TableCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> TableOut:
    if crud.get_table_by_code(db, payload.code):
        raise HTTPException(status_code=400, detail="表 code 已存在")
    return table_out(crud.create_table(db, payload))


@router.put("/{table_id}", response_model=TableOut, summary="更新数据表")
def update_table(
    table_id: int,
    payload: TableUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> TableOut:
    table = crud.get_table(db, table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="数据表不存在")
    return table_out(crud.update_table(db, table, payload))


@router.delete("/{table_id}", summary="删除数据表")
def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    table = crud.get_table(db, table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="数据表不存在")
    crud.delete_table(db, table)
    return {"ok": True}
