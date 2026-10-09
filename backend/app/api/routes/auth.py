from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.permissions import effective_permissions, is_admin
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import LoginRequest, Token
from app.schemas.user import UserPublic
from app.services.auth import AuthError, authenticate

router = APIRouter(prefix="/auth", tags=["认证"])


def _issue_token(db: Session, username: str, password: str) -> Token:
    try:
        user = authenticate(db, username, password)
    except AuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()

    return Token(access_token=create_access_token(subject=user.username))


@router.post("/login", response_model=Token, summary="用户名密码登录(JSON)")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    return _issue_token(db, payload.username, payload.password)


@router.post("/token", response_model=Token, summary="OAuth2 表单登录(供 Swagger 使用)")
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    return _issue_token(db, form_data.username, form_data.password)


@router.get("/me", response_model=UserPublic, summary="获取当前登录用户")
def read_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPublic:
    data = UserPublic.model_validate(current_user)
    data.permissions = effective_permissions(db, current_user)
    data.is_admin = is_admin(current_user)
    return data


@router.get("/methods", summary="可用的登录方式")
def auth_methods() -> dict:
    return {
        "local": "local" in settings.AUTH_BACKENDS,
        "ldap": settings.LDAP_ENABLED and "ldap" in settings.AUTH_BACKENDS,
        "oidc": settings.OIDC_ENABLED,
        "oidc_login_url": f"{settings.API_V1_PREFIX}/auth/oidc/login"
        if settings.OIDC_ENABLED
        else None,
    }
