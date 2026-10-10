from __future__ import annotations

import base64
import json
import threading
import time
from dataclasses import dataclass, field, replace
from typing import Any, Optional

import httpx

from app.core.config import settings


class BaserowError(Exception):
    """Baserow 访问错误。"""


# ---------------- 令牌模式:一个源=一个工作区 ----------------
@dataclass
class BaserowSource:
    key: str
    url: str
    token: str
    tables: dict[str, str] = field(default_factory=dict)
    department_field: str = ""


@dataclass
class TableAccess:
    """访问某张表所需的上下文。"""

    url: str
    jwt: str = ""
    token: str = ""
    department_field: str = ""


def _user_mode() -> bool:
    return bool(settings.BASEROW_USER_EMAIL and settings.BASEROW_USER_PASSWORD)


def all_sources() -> list[BaserowSource]:
    if settings.BASEROW_SOURCES:
        return [
            BaserowSource(
                key=key,
                url=str((raw or {}).get("url") or settings.BASEROW_URL),
                token=str((raw or {}).get("token") or ""),
                tables={str(k): str(v) for k, v in ((raw or {}).get("tables") or {}).items()},
                department_field=str(
                    (raw or {}).get("department_field", settings.BASEROW_DEPARTMENT_FIELD)
                ),
            )
            for key, raw in settings.BASEROW_SOURCES.items()
        ]
    return [
        BaserowSource(
            key="默认",
            url=settings.BASEROW_URL,
            token=settings.BASEROW_TOKEN,
            tables=dict(settings.BASEROW_TABLES),
            department_field=settings.BASEROW_DEPARTMENT_FIELD,
        )
    ]


# ---------------- 用户模式的会话与发现(带缓存) ----------------
_session_lock = threading.Lock()
_session: dict[str, Any] = {"jwt": None, "exp": 0.0}
_discovery_lock = threading.Lock()
_discovery: dict[str, Any] = {"data": None, "ts": 0.0}
_DISCOVERY_TTL = 300.0


def _login() -> tuple[str, float]:
    url = f"{settings.BASEROW_URL.rstrip('/')}/api/user/token-auth/"
    try:
        resp = httpx.post(
            url,
            json={
                "username": settings.BASEROW_USER_EMAIL,
                "password": settings.BASEROW_USER_PASSWORD,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        jwt = resp.json()["token"]
    except Exception as exc:  # noqa: BLE001
        raise BaserowError(f"Baserow 登录失败: {exc}")
    try:
        payload = jwt.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = float(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except Exception:  # noqa: BLE001
        exp = time.time() + 540
    return jwt, exp


def _jwt(force: bool = False) -> str:
    with _session_lock:
        if not force and _session["jwt"] and time.time() < _session["exp"] - 30:
            return _session["jwt"]
    jwt, exp = _login()
    with _session_lock:
        _session["jwt"] = jwt
        _session["exp"] = exp
    return jwt


def discover_databases(force: bool = False) -> list[dict[str, Any]]:
    """用用户身份列出所有数据库与表(按配置的工作区过滤)。"""
    with _discovery_lock:
        if not force and _discovery["data"] is not None and time.time() - _discovery["ts"] < _DISCOVERY_TTL:
            return _discovery["data"]

    jwt = _jwt()
    url = f"{settings.BASEROW_URL.rstrip('/')}/api/applications/"
    try:
        resp = httpx.get(url, headers={"Authorization": f"JWT {jwt}"}, timeout=20.0)
        resp.raise_for_status()
        apps = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise BaserowError(f"无法列出 Baserow 数据库: {exc}")

    allowed = set(settings.BASEROW_WORKSPACES)
    databases: list[dict[str, Any]] = []
    for app in apps:
        ws = app.get("workspace") or {}
        ws_name = ws.get("name") if isinstance(ws, dict) else str(ws)
        if allowed and ws_name not in allowed:
            continue
        databases.append(
            {
                "workspace": ws_name,
                "database": app.get("name"),
                "tables": [
                    {"id": str(t["id"]), "name": t["name"]} for t in app.get("tables", [])
                ],
            }
        )
    with _discovery_lock:
        _discovery["data"] = databases
        _discovery["ts"] = time.time()
    return databases


def all_datasets() -> list[dict[str, str]]:
    """全部数据集(供前端选择);key 全局唯一。"""
    if _user_mode():
        datasets: list[dict[str, str]] = []
        for db in discover_databases():
            for t in db["tables"]:
                datasets.append(
                    {
                        "key": f"{db['workspace']}/{db['database']}/{t['name']}",
                        "name": f"{db['database']}/{t['name']}",
                        "table_id": t["id"],
                        "source": db["workspace"],
                    }
                )
        return datasets

    datasets = []
    for source in all_sources():
        for name, table_id in source.tables.items():
            datasets.append(
                {
                    "key": f"{source.key}/{name}",
                    "name": name,
                    "table_id": table_id,
                    "source": source.key,
                }
            )
    return datasets


def resolve_table(table_id: str) -> Optional[TableAccess]:
    """按表 ID 解析访问上下文(自动匹配令牌/会话)。"""
    if _user_mode():
        for db in discover_databases():
            if any(t["id"] == table_id for t in db["tables"]):
                return TableAccess(
                    url=settings.BASEROW_URL,
                    jwt=_jwt(),
                    department_field=settings.BASEROW_DEPARTMENT_FIELD,
                )
        return None
    for source in all_sources():
        if table_id in set(source.tables.values()):
            return TableAccess(
                url=source.url, token=source.token, department_field=source.department_field
            )
    return None


# ---------------- 请求 ----------------
def _client(access: TableAccess) -> httpx.Client:
    if access.jwt:
        headers = {"Authorization": f"JWT {access.jwt}"}
    elif access.token:
        headers = {"Authorization": f"Token {access.token}"}
    else:
        raise BaserowError("数据源未配置凭据")
    return httpx.Client(base_url=f"{access.url.rstrip('/')}/api", headers=headers, timeout=20.0)


def _request(access: TableAccess, method: str, path: str, **kwargs: Any) -> httpx.Response:
    def do(acc: TableAccess) -> httpx.Response:
        with _client(acc) as client:
            return client.request(method, path, **kwargs)

    resp = do(access)
    if resp.status_code == 401 and access.jwt:
        access = replace(access, jwt=_jwt(force=True))
        resp = do(access)
    return resp


def _handle(resp: httpx.Response, action: str) -> Any:
    if resp.status_code >= 400:
        try:
            body = resp.json()
            detail = body.get("detail") or body.get("error") or ""
        except Exception:  # noqa: BLE001
            detail = resp.text[:200]
        raise BaserowError(f"{action}失败({resp.status_code}): {detail}")
    return resp.json() if resp.content else None


def _enabled() -> None:
    if not settings.BASEROW_ENABLED:
        raise BaserowError("Baserow 未启用")


def list_fields(access: TableAccess, table_id: str) -> list[dict[str, Any]]:
    _enabled()
    return _handle(_request(access, "GET", f"/database/fields/table/{table_id}/"), "获取字段")


def list_rows(
    access: TableAccess,
    table_id: str,
    *,
    page: int = 1,
    size: int = 50,
    search: Optional[str] = None,
    filters: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    _enabled()
    params: dict[str, Any] = {"user_field_names": "true", "page": page, "size": size}
    if search:
        params["search"] = search
    for key, value in (filters or {}).items():
        params[key] = value
    return _handle(
        _request(access, "GET", f"/database/rows/table/{table_id}/", params=params), "读取数据"
    )


def get_row(access: TableAccess, table_id: str, row_id: int) -> dict[str, Any]:
    _enabled()
    return _handle(
        _request(
            access,
            "GET",
            f"/database/rows/table/{table_id}/{row_id}/",
            params={"user_field_names": "true"},
        ),
        "读取记录",
    )


def create_row(access: TableAccess, table_id: str, data: dict[str, Any]) -> dict[str, Any]:
    _enabled()
    return _handle(
        _request(
            access,
            "POST",
            f"/database/rows/table/{table_id}/",
            params={"user_field_names": "true"},
            json=data,
        ),
        "新增记录",
    )


def update_row(
    access: TableAccess, table_id: str, row_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    _enabled()
    return _handle(
        _request(
            access,
            "PATCH",
            f"/database/rows/table/{table_id}/{row_id}/",
            params={"user_field_names": "true"},
            json=data,
        ),
        "更新记录",
    )


def delete_row(access: TableAccess, table_id: str, row_id: int) -> None:
    _enabled()
    _handle(_request(access, "DELETE", f"/database/rows/table/{table_id}/{row_id}/"), "删除记录")
