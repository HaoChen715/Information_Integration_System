from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.common import UTCDatetime


class UserBase(BaseModel):
    username: str
    # 注意:AD 内网邮箱常为 *.local 等保留域名,不能用 EmailStr 严格校验
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserPublic(UserBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    is_active: bool
    is_superuser: bool
    is_admin: bool = False
    auth_source: str = "local"
    department: Optional[str] = None
    created_at: UTCDatetime
    last_login_at: Optional[UTCDatetime] = None
    roles: list[str] = Field(default_factory=list, validation_alias=AliasChoices("role_codes"))
    permissions: dict[str, str] = Field(default_factory=dict)

