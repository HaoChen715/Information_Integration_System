"""Baserow 数据源的网页配置接口(仅管理员)。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.config import settings
from app.db.session import get_db
from app.models.baserow_config import BaserowSourceConfig, BaserowTableConfig
from app.models.department import Department
from app.models.user import User
from app.schemas.baserow_config import (
    BaserowFieldsIn,
    BaserowOptionsOut,
    BaserowSourceIn,
    BaserowSourceOut,
    BaserowTableOut,
    BaserowTestIn,
)
from app.services import baserow
from app.services.baserow import BaserowError

router = APIRouter(prefix="/admin/baserow", tags=["数据源配置"])


def _out(row: BaserowSourceConfig) -> BaserowSourceOut:
    return BaserowSourceOut(
        id=row.id,
        name=row.name,
        url=row.url,
        token_set=bool(row.token),
        token_hint=f"****{row.token[-4:]}" if row.token else "",
        department_field=row.department_field,
        enabled=row.enabled,
        tables=[
            BaserowTableOut(id=t.id, name=t.name, table_id=t.table_id, enabled=t.enabled)
            for t in row.tables
        ],
    )


@router.get("/sources", response_model=list[BaserowSourceOut], summary="数据源列表")
def list_sources(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[BaserowSourceOut]:
    rows = db.execute(select(BaserowSourceConfig).order_by(BaserowSourceConfig.id)).scalars()
    return [_out(row) for row in rows]


@router.get("/options", response_model=BaserowOptionsOut, summary="配置默认项")
def options(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> BaserowOptionsOut:
    names = list(db.execute(select(Department.name).order_by(Department.id)).scalars())
    return BaserowOptionsOut(default_url=settings.BASEROW_URL, departments=names)


@router.post("/fields", summary="获取表字段")
def table_fields(
    payload: BaserowFieldsIn,
    _: User = Depends(get_current_admin),
) -> list[dict]:
    try:
        return baserow.list_table_fields(payload.url, payload.token, payload.table_id)
    except BaserowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sources", response_model=BaserowSourceOut, summary="新增数据源")
def create_source(
    payload: BaserowSourceIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> BaserowSourceOut:
    if db.execute(select(BaserowSourceConfig).where(BaserowSourceConfig.name == payload.name)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="数据源名称已存在")
    if not payload.token:
        raise HTTPException(status_code=400, detail="新建数据源必须提供令牌")
    row = BaserowSourceConfig(
        name=payload.name,
        url=payload.url,
        token=payload.token,
        department_field=payload.department_field,
        enabled=payload.enabled,
    )
    for t in payload.tables:
        row.tables.append(BaserowTableConfig(name=t.name, table_id=t.table_id, enabled=t.enabled))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.put("/sources/{source_id}", response_model=BaserowSourceOut, summary="更新数据源")
def update_source(
    source_id: int,
    payload: BaserowSourceIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> BaserowSourceOut:
    row = db.get(BaserowSourceConfig, source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="数据源不存在")
    dup = db.execute(
        select(BaserowSourceConfig).where(
            BaserowSourceConfig.name == payload.name, BaserowSourceConfig.id != source_id
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="数据源名称已存在")

    row.name = payload.name
    row.url = payload.url
    if payload.token:
        row.token = payload.token
    row.department_field = payload.department_field
    row.enabled = payload.enabled
    row.tables.clear()
    db.flush()
    for t in payload.tables:
        row.tables.append(BaserowTableConfig(name=t.name, table_id=t.table_id, enabled=t.enabled))
    db.commit()
    db.refresh(row)
    return _out(row)


@router.delete("/sources/{source_id}", summary="删除数据源")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    row = db.get(BaserowSourceConfig, source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="数据源不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/test", summary="测试连接")
def test_connection(
    payload: BaserowTestIn,
    _: User = Depends(get_current_admin),
) -> dict:
    try:
        return baserow.test_table(payload.url, payload.token, payload.table_id)
    except BaserowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
