from __future__ import annotations

import ssl
from typing import Optional

from ldap3 import ALL, SIMPLE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException, LDAPSocketOpenError
from ldap3.utils.conv import escape_filter_chars
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.services.auth.base import AuthError, AuthIdentity

ACCOUNTDISABLE = 0x2


def _make_tls() -> Optional[Tls]:
    """内网 CA 自签时,指定 CA 或跳过校验。"""
    if not settings.LDAP_CA_CERT and not settings.LDAP_TLS_INSECURE:
        return None
    validate = ssl.CERT_NONE if settings.LDAP_TLS_INSECURE else ssl.CERT_REQUIRED
    return Tls(validate=validate, ca_certs_file=settings.LDAP_CA_CERT or None)


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
        tls=_make_tls(),
        get_info=ALL,
        connect_timeout=settings.LDAP_CONNECT_TIMEOUT,
    )


def _connect(server: Server, user: Optional[str], password: Optional[str]) -> Connection:
    """建立连接并按需 StartTLS(不执行 bind)。"""
    conn = Connection(
        server,
        user=user,
        password=password,
        authentication=SIMPLE,
        receive_timeout=settings.LDAP_CONNECT_TIMEOUT,
    )
    if settings.LDAP_USE_STARTTLS and not server.ssl:
        conn.open()
        conn.start_tls()
    return conn


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
            service_conn = _connect(
                server,
                settings.LDAP_BIND_DN or None,
                settings.LDAP_BIND_PASSWORD or None,
            )
            if not service_conn.bind():
                raise AuthError("认证服务配置异常", 503)
        except LDAPSocketOpenError:
            raise AuthError("认证服务暂不可用", 503)
        except LDAPException as exc:
            raise AuthError(f"认证服务连接失败: {exc}", 503)

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
            user_conn = _connect(server, user_dn, password)
            if not user_conn.bind():
                return None
        except LDAPSocketOpenError:
            raise AuthError("认证服务暂不可用", 503)
        except LDAPException as exc:
            raise AuthError(f"认证服务连接失败: {exc}", 503)
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
