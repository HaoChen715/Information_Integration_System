from typing import Optional

from pydantic import BaseModel, ConfigDict


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    resource: str
    action: str


class PermissionGroup(BaseModel):
    resource: str
    label: str
    permissions: list[PermissionOut]


class PermissionGrant(BaseModel):
    code: str
    data_scope: str = "self"


class RoleCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_admin: bool = False
    permissions: list[PermissionGrant] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_admin: Optional[bool] = None
    permissions: Optional[list[PermissionGrant]] = None


class RoleOut(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_system: bool
    is_admin: bool
    permissions: list[PermissionGrant] = []


class UserAdminOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    is_superuser: bool
    auth_source: str
    roles: list[str] = []
    permissions: dict[str, str] = {}
    direct_permissions: list[PermissionGrant] = []


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class UserRolesUpdate(BaseModel):
    roles: list[str]


class UserPermissionsUpdate(BaseModel):
    permissions: list[PermissionGrant]
