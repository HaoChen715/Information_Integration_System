from __future__ import annotations

from typing import Any, Optional

import httpx

from app.core.config import settings


class BaserowError(Exception):
    """Baserow 访问错误。"""


def _client() -> httpx.Client:
    if not settings.BASEROW_ENABLED:
        raise BaserowError("Baserow 未启用")
    if not settings.BASEROW_TOKEN:
        raise BaserowError("未配置 Baserow 令牌")
    return httpx.Client(
        base_url=f"{settings.BASEROW_URL.rstrip('/')}/api",
        headers={"Authorization": f"Token {settings.BASEROW_TOKEN}"},
        timeout=20.0,
    )


def _handle(resp: httpx.Response, action: str) -> Any:
    if resp.status_code >= 400:
        detail = ""
        try:
            detail = resp.json().get("detail") or resp.json().get("error") or ""
        except Exception:  # noqa: BLE001
            detail = resp.text[:200]
        raise BaserowError(f"{action}失败({resp.status_code}): {detail}")
    return resp.json() if resp.content else None


def list_fields(table_id: str) -> list[dict[str, Any]]:
    with _client() as client:
        return _handle(
            client.get(f"/database/fields/table/{table_id}/"), "获取字段"
        )


def list_rows(
    table_id: str,
    *,
    page: int = 1,
    size: int = 50,
    search: Optional[str] = None,
    filters: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"user_field_names": "true", "page": page, "size": size}
    if search:
        params["search"] = search
    # filters 的 key 已是完整的 Baserow 过滤参数名
    for key, value in (filters or {}).items():
        params[key] = value
    with _client() as client:
        return _handle(
            client.get(f"/database/rows/table/{table_id}/", params=params), "读取数据"
        )


def get_row(table_id: str, row_id: int) -> dict[str, Any]:
    with _client() as client:
        return _handle(
            client.get(
                f"/database/rows/table/{table_id}/{row_id}/",
                params={"user_field_names": "true"},
            ),
            "读取记录",
        )


def create_row(table_id: str, data: dict[str, Any]) -> dict[str, Any]:
    with _client() as client:
        return _handle(
            client.post(
                f"/database/rows/table/{table_id}/",
                params={"user_field_names": "true"},
                json=data,
            ),
            "新增记录",
        )


def update_row(table_id: str, row_id: int, data: dict[str, Any]) -> dict[str, Any]:
    with _client() as client:
        return _handle(
            client.patch(
                f"/database/rows/table/{table_id}/{row_id}/",
                params={"user_field_names": "true"},
                json=data,
            ),
            "更新记录",
        )


def delete_row(table_id: str, row_id: int) -> None:
    with _client() as client:
        _handle(
            client.delete(f"/database/rows/table/{table_id}/{row_id}/"), "删除记录"
        )
