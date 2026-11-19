from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_table import DataField, DataRecord, DataTable
from app.models.user import User
from app.schemas.data_table import FieldDef, TableCreate, TableUpdate


def list_tables(db: Session) -> list[DataTable]:
    return list(db.execute(select(DataTable).order_by(DataTable.id)).scalars())


def get_table(db: Session, table_id: int) -> Optional[DataTable]:
    return db.get(DataTable, table_id)


def get_table_by_code(db: Session, code: str) -> Optional[DataTable]:
    return db.execute(select(DataTable).where(DataTable.code == code)).scalar_one_or_none()


def _replace_fields(db: Session, table: DataTable, fields: list[FieldDef]) -> None:
    table.fields.clear()
    db.flush()
    for i, f in enumerate(fields):
        table.fields.append(
            DataField(
                key=f.key,
                label=f.label,
                type=f.type,
                required=f.required,
                order=i,
                options=[o.model_dump() for o in f.options],
            )
        )


def create_table(db: Session, data: TableCreate) -> DataTable:
    table = DataTable(
        code=data.code,
        name=data.name,
        description=data.description,
        title_field=data.title_field,
        scope_by_department=data.scope_by_department,
        visible_departments=list(data.visible_departments or []),
        department_field=data.department_field,
    )
    _replace_fields(db, table, data.fields)
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


def update_table(db: Session, table: DataTable, data: TableUpdate) -> DataTable:
    if data.name is not None:
        table.name = data.name
    if data.description is not None:
        table.description = data.description
    if data.title_field is not None:
        table.title_field = data.title_field
    if data.scope_by_department is not None:
        table.scope_by_department = data.scope_by_department
    if data.visible_departments is not None:
        table.visible_departments = list(data.visible_departments)
    if data.department_field is not None:
        table.department_field = data.department_field
    if data.fields is not None:
        _replace_fields(db, table, data.fields)
    db.commit()
    db.refresh(table)
    return table


def delete_table(db: Session, table: DataTable) -> None:
    db.delete(table)
    db.commit()


# ---------------- 记录与数据范围 ----------------
def table_visible(table: DataTable, user: User, is_global: bool) -> bool:
    if is_global or not table.scope_by_department:
        return True
    depts = table.visible_departments or []
    if not depts:
        return True
    return bool(user.department) and user.department in depts


def record_visible(table: DataTable, record: DataRecord, user: User, scope: str, is_global: bool) -> bool:
    if is_global or scope == "all":
        return True
    if scope == "self":
        return record.owner_username == user.username
    return table_visible(table, user, is_global)


def list_records(
    db: Session,
    table: DataTable,
    user: User,
    scope: str,
    is_global: bool,
    search: Optional[str] = None,
) -> list[DataRecord]:
    stmt = select(DataRecord).where(DataRecord.table_id == table.id)
    if not (is_global or scope == "all"):
        if scope == "self":
            stmt = stmt.where(DataRecord.owner_username == user.username)
        elif not table_visible(table, user, is_global):
            return []
    records = list(db.execute(stmt.order_by(DataRecord.id.desc())).scalars())
    if search:
        q = search.lower()
        records = [
            r
            for r in records
            if q in str(r.data).lower() or q in r.owner_username.lower()
        ]
    return records


def get_record(db: Session, table: DataTable, record_id: int) -> Optional[DataRecord]:
    record = db.get(DataRecord, record_id)
    if record is None or record.table_id != table.id:
        return None
    return record


def create_record(db: Session, table: DataTable, user: User, data: dict) -> DataRecord:
    department = None
    if table.scope_by_department:
        depts = table.visible_departments or []
        if user.department and (not depts or user.department in depts):
            department = user.department
        elif depts:
            department = depts[0]
        else:
            department = user.department
    record = DataRecord(
        table_id=table.id,
        data=data,
        owner_username=user.username,
        department=department,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_record(db: Session, record: DataRecord, data: dict) -> DataRecord:
    record.data = data
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: DataRecord) -> None:
    db.delete(record)
    db.commit()
