from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UTCDatetime


class RecordCreate(BaseModel):
    title: str
    content: Optional[str] = None


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: Optional[str] = None
    owner_username: str
    department: Optional[str] = None
    created_at: UTCDatetime
