from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.common import UTCDatetime


class SelectOption(BaseModel):
    value: str
    color: str = "gray"


class FieldDef(BaseModel):
    key: str
    label: str
    type: str = "text"
    required: bool = False
    options: list[SelectOption] = []


class FieldOut(FieldDef):
    id: int


class TableCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    title_field: str = ""
    scope_by_department: bool = True
    department_field: str = ""
    fields: list[FieldDef] = []


class TableUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    title_field: Optional[str] = None
    scope_by_department: Optional[bool] = None
    department_field: Optional[str] = None
    fields: Optional[list[FieldDef]] = None


class TableOut(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    title_field: str
    scope_by_department: bool
    department_field: str = ""
    fields: list[FieldOut] = []


class RecordCreate(BaseModel):
    data: dict[str, Any] = {}


class RecordUpdate(BaseModel):
    data: dict[str, Any]


class RecordOut(BaseModel):
    id: int
    data: dict[str, Any]
    owner_username: str
    department: Optional[str] = None
    created_at: UTCDatetime
    updated_at: UTCDatetime
