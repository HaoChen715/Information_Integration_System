"""创建测试用户。

用法(在 backend/ 目录下):
    python -m scripts.create_user admin admin123 --superuser
    python -m scripts.create_user zhangsan pass123 --full-name 张三 --email zs@example.com
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crud import user as user_crud  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.schemas.user import UserCreate  # noqa: E402
import app.models  # noqa: E402,F401


def main() -> None:
    parser = argparse.ArgumentParser(description="创建本地测试用户")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--email", default=None)
    parser.add_argument("--full-name", default=None)
    parser.add_argument("--superuser", action="store_true")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if user_crud.get_by_username(db, args.username):
            print(f"用户已存在: {args.username}")
            return
        user = user_crud.create_user(
            db,
            UserCreate(
                username=args.username,
                password=args.password,
                email=args.email,
                full_name=args.full_name,
            ),
            is_superuser=args.superuser,
        )
        print(f"已创建用户: {user.username} (id={user.id}, superuser={user.is_superuser})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
