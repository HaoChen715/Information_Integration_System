from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


def get_by_username(db: Session, username: str) -> Optional[User]:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def create_user(db: Session, data: UserCreate, *, is_superuser: bool = False) -> User:
    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    user = get_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
