from typing import Optional

from pydantic import BaseModel


class BaserowTableIn(BaseModel):
    name: str
    table_id: str
    enabled: bool = True


class BaserowTableOut(BaserowTableIn):
    id: int


class BaserowSourceIn(BaseModel):
    name: str
    url: str
    token: Optional[str] = None  # 新建必填;更新留空表示不变
    department_field: str = ""
    enabled: bool = True
    tables: list[BaserowTableIn] = []


class BaserowSourceOut(BaseModel):
    id: int
    name: str
    url: str
    token_set: bool
    token_hint: str
    department_field: str
    enabled: bool
    tables: list[BaserowTableOut] = []


class BaserowTestIn(BaseModel):
    url: str
    token: str
    table_id: str
