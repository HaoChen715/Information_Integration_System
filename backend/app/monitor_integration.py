"""内置「行情监控系统」(vended from basis_monitor)作为子应用挂载到 /monitor。

通过 importlib 以独立模块名加载,避免与本站 `app` 包重名;数据目录用环境变量
`BASIS_MONITOR_DATA` 指向持久化目录。
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

VENDOR_DIR = Path(__file__).resolve().parent.parent / "third_party" / "basis_monitor"

_module: Any = None


def _load() -> Any:
    global _module
    if _module is not None:
        return _module

    data_dir = os.environ.get("BASIS_MONITOR_DATA") or str(Path.cwd() / "data" / "monitor")
    os.environ.setdefault("BASIS_MONITOR_DATA", data_dir)

    spec = importlib.util.spec_from_file_location(
        "basis_monitor_service", VENDOR_DIR / "app.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 basis_monitor 子应用")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _module = module
    return module


def create_wsgi_app() -> Any:
    """返回 basis_monitor 的 WSGI 应用,供 Starlette 挂载。"""
    return _load().app


def start_engine() -> None:
    """启动行情抓取/告警引擎(失败不影响主服务)。"""
    try:
        _load()._engine.start()
    except Exception:  # noqa: BLE001
        pass
