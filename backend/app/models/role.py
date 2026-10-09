from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.permission import RolePermission
    from app.models.user import User

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    # 系统内置角色不可删除
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 管理员角色:仅超级管理员可授予
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 部门主管角色:可管理本部门员工的权限
    is_department_manager: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
    permission_links: Mapped[list["RolePermission"]] = relationship(
        cascade="all, delete-orphan"
    )
