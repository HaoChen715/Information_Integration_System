"""极简的 SQLite 兼容迁移:补齐新增列(无 Alembic 时的兜底)。"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# (表, 列, 建列 DDL 片段)
_ADDED_COLUMNS = [
    ("users", "department", "VARCHAR(128)"),
    ("users", "last_seen_at", "DATETIME"),
    ("users", "avatar_ext", "VARCHAR(8)"),
    ("users", "avatar_updated_at", "DATETIME"),
    ("roles", "is_system", "BOOLEAN NOT NULL DEFAULT 0"),
    ("roles", "is_admin", "BOOLEAN NOT NULL DEFAULT 0"),
    ("roles", "is_department_manager", "BOOLEAN NOT NULL DEFAULT 0"),
]


def ensure_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table, column, ddl in _ADDED_COLUMNS:
        if table not in tables:
            continue
        existing = {col["name"] for col in inspector.get_columns(table)}
        if column in existing:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
