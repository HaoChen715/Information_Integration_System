from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserPublic(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
