from __future__ import annotations

from typing import Optional

from ldap3 import ALL, SIMPLE, Connection, Server
from ldap3.core.exceptions import LDAPException, LDAPSocketOpenError
from ldap3.utils.conv import escape_filter_chars
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.services.auth.base import AuthError, AuthIdentity

ACCOUNTDISABLE = 0x2


def _parse_server(url: str) -> Server:
    """解析 ldap:// 或 ldaps:// 地址,返回 ldap3 Server。"""
    use_ssl = url.lower().startswith("ldaps://")
    host = url.split("://", 1)[-1]
    port = 636 if use_ssl else 389
    if ":" in host:
        host, _, raw_port = host.partition(":")
        port = int(raw_port)
    return Server(
        host,
        port=port,
        use_ssl=use_ssl,
        get_info=ALL,
        connect_timeout=settings.LDAP_CONNECT_TIMEOUT,
    )


def _normalize(raw: str) -> str:
    """统一账号输入:支持 sAMAccountName、UPN、DOMAIN\\user。"""
    raw = raw.strip()
    if "\\" in raw:
        return raw.split("\\", 1)[1]
    return raw


def _values(entry, attribute: str) -> list[str]:
    if attribute not in entry:
        return []
    value = entry[attribute].value
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [str(value)]


def _single(entry, attribute: str) -> Optional[str]:
    values = _values(entry, attribute)
    return values[0] if values else None


class LdapAuthProvider:
    """AD 域认证:服务账号搜索用户 DN -> 用用户 DN + 密码重新绑定。"""

    name = "ldap"

    def authenticate(self, db: Session, username: str, password: str) -> Optional[User]:
        if not settings.LDAP_ENABLED or not password:
            return None

        name = _normalize(username)
        server = _parse_server(settings.LDAP_SERVER)

        # ① 服务账号绑定(用于搜索)
        try:
            service_conn = Connection(
                server,
                user=settings.LDAP_BIND_DN or None,
                password=settings.LDAP_BIND_PASSWORD or None,
                authentication=SIMPLE,
                receive_timeout=settings.LDAP_CONNECT_TIMEOUT,
            )
            if not service_conn.bind():
                raise AuthError("认证服务配置异常", 503)
        except LDAPSocketOpenError:
            raise AuthError("认证服务暂不可用", 503)

        # ② 搜索用户
        safe = escape_filter_chars(name)
        search_filter = (
            "(&(objectClass=user)"
            f"(|(sAMAccountName={safe})(userPrincipalName={safe})))"
        )
        try:
            service_conn.search(
                settings.LDAP_BASE_DN,
                search_filter,
                attributes=[
                    "sAMAccountName",
                    "userPrincipalName",
                    "mail",
                    "displayName",
                    "memberOf",
                    "userAccountControl",
                    "objectGUID",
                ],
            )
        except LDAPException:
            raise AuthError("认证服务查询失败", 503)

        if not service_conn.entries:
            return None

        entry = service_conn.entries[0]

        # 账号禁用检查
        uac = _single(entry, "userAccountControl")
        if uac is not None:
            try:
                if int(uac) & ACCOUNTDISABLE:
                    raise AuthError("账号已被禁用", 403)
            except (TypeError, ValueError):
                pass

        # ③ 用用户 DN + 密码绑定,验证凭证
        user_dn = entry.entry_dn
        try:
            user_conn = Connection(
                server,
                user=user_dn,
                password=password,
                authentication=SIMPLE,
                receive_timeout=settings.LDAP_CONNECT_TIMEOUT,
            )
            if not user_conn.bind():
                return None
        except LDAPSocketOpenError:
            raise AuthError("认证服务暂不可用", 503)
        finally:
            try:
                service_conn.unbind()
            except LDAPException:
                pass

        account = _single(entry, "sAMAccountName") or name
        return AuthIdentity(
            username=account,
            auth_source="ad",
            email=_single(entry, "mail"),
            full_name=_single(entry, "displayName"),
            groups=_values(entry, "memberOf"),
            external_id=_single(entry, "objectGUID"),
        )
