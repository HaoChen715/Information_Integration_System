"""为内置行情监控子应用(/monitor)做统一认证与权限桥接。

本系统已用 JWT 登录;该中间件校验前端携带的 Cookie/Authorization 中的 JWT,
解析出用户与在本系统中的有效权限(含数据范围),再以请求头注入给 Flask 子应用,
从而**移除子应用自身的登录/用户体系**,复用本系统的账号与 RBAC。
"""

from __future__ import annotations

from urllib.parse import quote

from jwt import InvalidTokenError
from sqlalchemy import select
from starlette.responses import JSONResponse, RedirectResponse

from app.core.permissions import effective_permissions, is_admin
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User

PREFIX = "/monitor"


def _resolve_user(token: str) -> User | None:
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        return None
    username = payload.get("sub")
    if not username:
        return None
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        # 触发关系加载需要会话存活,这里直接构造需要的值
        user._iis_perms = effective_permissions(db, user)  # type: ignore[attr-defined]
        user._iis_admin = is_admin(user)  # type: ignore[attr-defined]
        return user
    finally:
        db.close()


def _dept_usernames(department: str | None) -> list[str]:
    if not department:
        return []
    db = SessionLocal()
    try:
        rows = db.execute(select(User.username).where(User.department == department)).scalars()
        return list(rows)
    finally:
        db.close()


async def monitor_auth_middleware(request, call_next):
    if not request.url.path.startswith(PREFIX):
        return await call_next(request)

    token = request.cookies.get("iis_token")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]

    user = _resolve_user(token) if token else None
    if user is None:
        if "text/html" in request.headers.get("accept", ""):
            return RedirectResponse(f"/login?redirect={request.url.path}")
        return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)

    admin = getattr(user, "_iis_admin", False)
    perms = getattr(user, "_iis_perms", {})

    view_scope = "all" if admin else perms.get("monitor:view")
    if not view_scope:
        return JSONResponse({"ok": False, "error": "无权访问行情监控"}, status_code=403)
    edit_scope = "all" if admin else perms.get("monitor:edit", "")
    delete_scope = "all" if admin else perms.get("monitor:delete", "")
    can_create = "1" if (admin or "monitor:create" in perms) else "0"

    dept_owners: list[str] = []
    if not admin and "dept" in (view_scope, edit_scope, delete_scope):
        dept_owners = _dept_usernames(user.department)

    injected = {
        b"x-iis-user": quote(user.username).encode(),
        b"x-iis-role": (b"admin" if admin else b"user"),
        b"x-iis-view-scope": view_scope.encode(),
        b"x-iis-edit-scope": (edit_scope or "").encode(),
        b"x-iis-delete-scope": (delete_scope or "").encode(),
        b"x-iis-create": can_create.encode(),
        b"x-iis-dept-owners": quote(",".join(dept_owners)).encode(),
    }
    headers = [
        (k, v) for k, v in request.scope["headers"] if not k.lower().startswith(b"x-iis-")
    ]
    headers.extend(injected.items())
    request.scope["headers"] = headers

    return await call_next(request)
