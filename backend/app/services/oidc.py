from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKSet
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.services.auth.base import AuthIdentity


class OidcError(Exception):
    """OIDC 流程中的业务错误。"""


def _verify():
    """TLS 校验参数:优先使用指定的 CA 证书,否则按 OIDC_VERIFY_SSL。"""
    if settings.OIDC_CA_CERT:
        return settings.OIDC_CA_CERT
    return settings.OIDC_VERIFY_SSL


@dataclass
class OidcEndpoints:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str


_discovery_cache: dict[str, tuple[float, OidcEndpoints]] = {}
_jwks_cache: dict[str, tuple[float, PyJWKSet]] = {}
_lock = threading.Lock()
_TTL = 3600.0


def _discover() -> OidcEndpoints:
    issuer = settings.OIDC_ISSUER.rstrip("/")
    with _lock:
        cached = _discovery_cache.get(issuer)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1]

    url = f"{issuer}/.well-known/openid-configuration"
    try:
        resp = httpx.get(url, timeout=10.0, verify=_verify())
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise OidcError(f"无法获取 OIDC 配置: {exc}")

    endpoints = OidcEndpoints(
        issuer=data["issuer"],
        authorization_endpoint=data["authorization_endpoint"],
        token_endpoint=data["token_endpoint"],
        jwks_uri=data["jwks_uri"],
    )
    with _lock:
        _discovery_cache[issuer] = (time.time(), endpoints)
    return endpoints


def _get_jwks() -> PyJWKSet:
    ep = _discover()
    with _lock:
        cached = _jwks_cache.get(ep.jwks_uri)
        if cached and time.time() - cached[0] < _TTL:
            return cached[1]

    try:
        resp = httpx.get(ep.jwks_uri, timeout=10.0, verify=_verify())
        resp.raise_for_status()
        jwks = PyJWKSet.from_dict(resp.json())
    except Exception as exc:  # noqa: BLE001
        raise OidcError(f"无法获取 JWKS: {exc}")

    with _lock:
        _jwks_cache[ep.jwks_uri] = (time.time(), jwks)
    return jwks


def make_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def create_txn_token(state: str, nonce: str, code_verifier: str, next_url: str) -> str:
    payload = {
        "state": state,
        "nonce": nonce,
        "cv": code_verifier,
        "next": next_url,
        "exp": int(time.time()) + 600,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_txn_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError:
        return None


def build_authorize_url(state: str, nonce: str, code_challenge: str) -> str:
    ep = _discover()
    params = {
        "response_type": "code",
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "scope": settings.OIDC_SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{ep.authorization_endpoint}?{urlencode(params)}"


def exchange_code(code: str, code_verifier: str) -> dict[str, Any]:
    ep = _discover()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "client_id": settings.OIDC_CLIENT_ID,
        "code_verifier": code_verifier,
    }
    auth = None
    if settings.OIDC_CLIENT_SECRET:
        auth = (settings.OIDC_CLIENT_ID, settings.OIDC_CLIENT_SECRET)
    try:
        resp = httpx.post(
            ep.token_endpoint,
            data=data,
            auth=auth,
            timeout=10.0,
            verify=_verify(),
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        raise OidcError(f"换取令牌失败: {exc}")


def verify_id_token(id_token: str, nonce: Optional[str]) -> dict[str, Any]:
    ep = _discover()
    try:
        header = jwt.get_unverified_header(id_token)
    except InvalidTokenError as exc:
        raise OidcError(f"id_token 格式错误: {exc}")

    kid = header.get("kid")
    jwks = _get_jwks()
    signing_key = None
    for key in jwks.keys:
        if kid is None or key.key_id == kid:
            signing_key = key
            break
    if signing_key is None:
        raise OidcError("未找到匹配的签名公钥")

    try:
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384"],
            audience=settings.OIDC_CLIENT_ID,
            issuer=ep.issuer,
        )
    except InvalidTokenError as exc:
        raise OidcError(f"id_token 校验失败: {exc}")

    if nonce and claims.get("nonce") != nonce:
        raise OidcError("nonce 校验失败")
    return claims


def claims_to_identity(claims: dict[str, Any]) -> AuthIdentity:
    username = (
        claims.get(settings.OIDC_USERNAME_CLAIM)
        or claims.get("preferred_username")
        or claims.get("email")
        or claims.get("sub")
    )
    raw_groups = claims.get(settings.OIDC_GROUPS_CLAIM) or []
    if isinstance(raw_groups, str):
        groups = [raw_groups]
    else:
        groups = [str(g) for g in raw_groups]

    return AuthIdentity(
        username=str(username),
        auth_source="oidc",
        email=claims.get(settings.OIDC_EMAIL_CLAIM),
        full_name=claims.get(settings.OIDC_NAME_CLAIM),
        groups=groups,
        external_id=claims.get("sub"),
    )
