from sqlalchemy.orm import Session

from app.core.avatars import avatar_url
from app.core.permissions import effective_permissions, is_admin, management_scope
from app.models.user import User
from app.schemas.user import UserPublic


def user_public(db: Session, user: User) -> UserPublic:
    """构建当前用户响应(含有效权限、是否管理员、头像地址)。"""
    data = UserPublic.model_validate(user)
    data.permissions = effective_permissions(db, user)
    data.is_admin = is_admin(user)
    data.manage_scope = management_scope(user)
    data.avatar_url = avatar_url(user)
    return data
