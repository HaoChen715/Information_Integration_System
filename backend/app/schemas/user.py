from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


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
    auth_source: str = "local"
    created_at: datetime
    last_login_at: Optional[datetime] = None
    roles: list[str] = Field(default_factory=list, validation_alias=AliasChoices("role_codes"))

