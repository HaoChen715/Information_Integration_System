from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.role import user_roles

if TYPE_CHECKING:
    from app.models.permission import UserPermission
    from app.models.role import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(128))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # 部门:数据范围 dept 过滤依据(可由 AD/OIDC 同步)
    department: Mapped[Optional[str]] = mapped_column(String(128), index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # local = 本地账号, ad = AD 域账号, oidc = 统一身份认证
    auth_source: Mapped[str] = mapped_column(String(16), default="local", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # 最近活跃时间:用于统计在线用户
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 头像文件扩展名(png/jpg/webp);为空表示使用首字母头像
    avatar_ext: Mapped[Optional[str]] = mapped_column(String(8))
    avatar_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")
    permission_links: Mapped[list["UserPermission"]] = relationship(
        cascade="all, delete-orphan"
    )

    @property
    def role_codes(self) -> list[str]:
        return [role.code for role in self.roles]

