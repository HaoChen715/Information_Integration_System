from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    pass


class BaserowSourceConfig(Base):
    """网页配置的 Baserow 数据源(通常对应一个工作区令牌)。"""

    __tablename__ = "baserow_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    department_field: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    # 可见部门(部门管理里的部门名);为空表示所有部门可见
    departments: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tables: Mapped[list["BaserowTableConfig"]] = relationship(
        cascade="all, delete-orphan", order_by="BaserowTableConfig.id"
    )


class BaserowTableConfig(Base):
    """数据源下的数据表。"""

    __tablename__ = "baserow_tables"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("baserow_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    table_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # 卡片标题所用字段名(留空则取首列)
    title_field: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
