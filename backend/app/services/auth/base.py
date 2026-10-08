from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class AuthError(Exception):
    """认证过程中需要反馈给前端的业务错误(如账号禁用、AD 不可达)。"""

    def __init__(self, detail: str, status_code: int = 401) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


@dataclass
class AuthIdentity:
    """认证成功后从认证源获取到的身份信息。"""

    username: str
    auth_source: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    groups: list[str] = field(default_factory=list)
    external_id: Optional[str] = None
