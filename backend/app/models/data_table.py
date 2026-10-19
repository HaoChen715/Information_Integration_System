"""原生「动态数据表」模型:元数据(表/字段)+ 记录(JSONB)。

替代 Baserow:管理员在网页定义表与字段,记录以 JSON 存储,便于灵活建模。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# SQLite 用 JSON,PostgreSQL 用 JSONB
JSONType = JSON().with_variant(JSONB(), "postgresql")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DataTable(Base):
    """数据表(数据集)定义。"""

    __tablename__ = "data_tables"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    # 卡片标题所用字段 key(留空取第一个字段)
    title_field: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    # 记录是否按部门过滤(便于公共表不做部门限制)
    scope_by_department: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # 部门取值所用字段 key(留空则取创建者的部门)
    department_field: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    fields: Mapped[list["DataField"]] = relationship(
        cascade="all, delete-orphan", order_by="DataField.order"
    )


class DataField(Base):
    """字段定义。type: text/long_text/number/date/boolean/single_select/multiple_select。"""

    __tablename__ = "data_fields"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("data_tables.id", ondelete="CASCADE"), index=True, nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 单选/多选的可选项:[{"value":"进行中","color":"blue"}]
    options: Mapped[list] = mapped_column(JSONType, default=list)


class DataRecord(Base):
    """记录:data 为 {字段key: 值} 的 JSON。"""

    __tablename__ = "data_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("data_tables.id", ondelete="CASCADE"), index=True, nullable=False
    )
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    owner_username: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
