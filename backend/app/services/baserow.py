from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from app.core.config import settings


class BaserowError(Exception):
    """Baserow 访问错误。"""


@dataclass
class BaserowSource:
    """一个 Baserow 数据源(通常对应一个工作区,有自己的令牌)。"""

    key: str
    url: str
    token: str
    tables: dict[str, str] = field(default_factory=dict)
    department_field: str = ""


def all_sources() -> list[BaserowSource]:
    """解析配置中的全部数据源;未配置多源时退回单源配置。"""
    if settings.BASEROW_SOURCES:
        sources: list[BaserowSource] = []
        for key, raw in settings.BASEROW_SOURCES.items():
            cfg: dict[str, Any] = raw if isinstance(raw, dict) else {}
            sources.append(
                BaserowSource(
                    key=key,
                    url=str(cfg.get("url") or settings.BASEROW_URL),
                    token=str(cfg.get("token") or ""),
                    tables={str(k): str(v) for k, v in (cfg.get("tables") or {}).items()},
                    department_field=str(
                        cfg.get("department_field", settings.BASEROW_DEPARTMENT_FIELD)
                    ),
                )
            )
        return sources
    return [
        BaserowSource(
            key="默认",
            url=settings.BASEROW_URL,
            token=settings.BASEROW_TOKEN,
            tables=dict(settings.BASEROW_TABLES),
            department_field=settings.BASEROW_DEPARTMENT_FIELD,
        )
    ]


def source_for_table(table_id: str) -> Optional[BaserowSource]:
    for source in all_sources():
        if table_id in set(source.tables.values()):
            return source
    return None


def all_datasets() -> list[dict[str, str]]:
    """所有数据源下的数据集;key 全局唯一(源/名称)。"""
    datasets: list[dict[str, str]] = []
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


def _client(source: BaserowSource) -> httpx.Client:
    if not source.token:
        raise BaserowError(f"数据源「{source.key}」未配置令牌")
    return httpx.Client(
        base_url=f"{source.url.rstrip('/')}/api",
        headers={"Authorization": f"Token {source.token}"},
        timeout=20.0,
    )


def _handle(resp: httpx.Response, action: str) -> Any:
    if resp.status_code >= 400:
        detail = ""
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


def list_fields(source: BaserowSource, table_id: str) -> list[dict[str, Any]]:
    _enabled()
    with _client(source) as client:
        return _handle(client.get(f"/database/fields/table/{table_id}/"), "获取字段")


def list_rows(
    source: BaserowSource,
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
    with _client(source) as client:
        return _handle(client.get(f"/database/rows/table/{table_id}/", params=params), "读取数据")


def get_row(source: BaserowSource, table_id: str, row_id: int) -> dict[str, Any]:
    _enabled()
    with _client(source) as client:
        return _handle(
            client.get(
                f"/database/rows/table/{table_id}/{row_id}/",
                params={"user_field_names": "true"},
            ),
            "读取记录",
        )


def create_row(source: BaserowSource, table_id: str, data: dict[str, Any]) -> dict[str, Any]:
    _enabled()
    with _client(source) as client:
        return _handle(
            client.post(
                f"/database/rows/table/{table_id}/",
                params={"user_field_names": "true"},
                json=data,
            ),
            "新增记录",
        )


def update_row(
    source: BaserowSource, table_id: str, row_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    _enabled()
    with _client(source) as client:
        return _handle(
            client.patch(
                f"/database/rows/table/{table_id}/{row_id}/",
                params={"user_field_names": "true"},
                json=data,
            ),
            "更新记录",
        )


def delete_row(source: BaserowSource, table_id: str, row_id: int) -> None:
    _enabled()
    with _client(source) as client:
        _handle(client.delete(f"/database/rows/table/{table_id}/{row_id}/"), "删除记录")
