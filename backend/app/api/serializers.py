from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.avatars import avatar_url
from app.core.permissions import effective_permissions, is_admin, management_scope
from app.models.permission import Permission
from app.models.user import User
from app.schemas.user import UserPublic


def user_public(db: Session, user: User) -> UserPublic:
    """构建当前用户响应(含有效权限、中文名、是否管理员、头像地址)。"""
    perms = effective_permissions(db, user)
    labels: dict[str, str] = {}
    if perms:
        labels = {
            code: name
            for code, name in db.execute(
                select(Permission.code, Permission.name).where(
                    Permission.code.in_(list(perms.keys()))
                )
            ).all()
        }

    data = UserPublic.model_validate(user)
    data.permissions = perms
    data.permission_labels = labels
    data.role_names = [role.name for role in user.roles]
    data.is_admin = is_admin(user)
    data.manage_scope = management_scope(user)
    data.avatar_url = avatar_url(user)
    return data
