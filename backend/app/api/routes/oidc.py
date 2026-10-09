from datetime import datetime, timezone
import logging
from typing import Optional
from urllib.parse import urlencode

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.crud import user as user_crud
from app.db.session import get_db
from app.services.auth.base import AuthError
from app.services.oidc import (
    OidcError,
    build_authorize_url,
    claims_to_identity,
    create_txn_token,
    decode_txn_token,
    exchange_code,
    make_pkce,
    verify_id_token,
)

router = APIRouter(prefix="/auth/oidc", tags=["OIDC 认证"])

logger = logging.getLogger(__name__)

COOKIE_NAME = "oidc_txn"


def _frontend_redirect(request: Request, **params: str) -> str:
    base = settings.OIDC_POST_LOGIN_REDIRECT
    if not base.startswith("http"):
        base = str(request.base_url).rstrip("/") + "/" + base.lstrip("/")
    return f"{base}#{urlencode(params)}"


@router.get("/login", summary="跳转到统一身份认证平台")
def oidc_login(
    request: Request,
    next_url: str = Query("/", alias="next"),
) -> RedirectResponse:
    if not settings.OIDC_ENABLED:
        raise HTTPException(status_code=404, detail="OIDC 未启用")

    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    verifier, challenge = make_pkce()

    try:
        authorize_url = build_authorize_url(state, nonce, challenge)
    except OidcError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    resp = RedirectResponse(authorize_url, status_code=302)
    resp.set_cookie(
        COOKIE_NAME,
        create_txn_token(state, nonce, verifier, next_url),
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.OIDC_COOKIE_SECURE,
        path="/",
    )
    return resp


@router.get("/callback", summary="统一身份认证回调")
def oidc_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    def finish(**params: str) -> RedirectResponse:
        response = RedirectResponse(_frontend_redirect(request, **params))
        response.delete_cookie(COOKIE_NAME, path="/")
        return response

    if error:
        return finish(error=error_description or error)

    txn_cookie = request.cookies.get(COOKIE_NAME)
    if not code or not state or not txn_cookie:
        return finish(error="登录会话已失效,请重试")

    txn = decode_txn_token(txn_cookie)
    if not txn or txn.get("state") != state:
        return finish(error="state 校验失败,请重试")

    try:
        tokens = exchange_code(code, txn["cv"])
        id_token = tokens.get("id_token")
        if not id_token:
            raise OidcError("统一认证未返回 id_token")

        claims = verify_id_token(id_token, txn.get("nonce"))
        identity = claims_to_identity(claims)
        user = user_crud.upsert_external_user(db, identity, settings.OIDC_GROUP_ROLE_MAP)
        if not user.is_active:
            return finish(error="账号已被禁用")

        user.last_login_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()

        token = create_access_token(subject=user.username)
        return finish(token=token, next=txn.get("next", "/"))
    except AuthError as exc:
        return finish(error=exc.detail)
    except OidcError as exc:
        return finish(error=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("OIDC 回调处理失败")
        return finish(error="登录失败,请联系管理员")
