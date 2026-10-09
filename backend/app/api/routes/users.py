from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.serializers import user_public
from app.core.avatars import ALLOWED_TYPES, EXT_MEDIA_TYPE, avatar_dir
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserPublic

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/{user_id}/avatar", summary="获取用户头像")
def get_avatar(user_id: int, db: Session = Depends(get_db)) -> FileResponse:
    user = db.get(User, user_id)
    if user is None or not user.avatar_ext:
        raise HTTPException(status_code=404, detail="无头像")
    path = avatar_dir() / f"{user.id}.{user.avatar_ext}"
    if not path.exists():
        raise HTTPException(status_code=404, detail="无头像")
    return FileResponse(
        path,
        media_type=EXT_MEDIA_TYPE.get(user.avatar_ext, "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=86400"},
    )


def _remove_file(user: User) -> None:
    if not user.avatar_ext:
        return
    path = avatar_dir() / f"{user.id}.{user.avatar_ext}"
    if path.exists():
        path.unlink()


@router.post("/me/avatar", response_model=UserPublic, summary="上传我的头像")
async def upload_my_avatar(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPublic:
    ext = ALLOWED_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(status_code=400, detail="仅支持 PNG / JPG / WebP 图片")

    data = await file.read()
    if len(data) > settings.AVATAR_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"图片不能超过 {settings.AVATAR_MAX_MB} MB")

    _remove_file(current)
    (avatar_dir() / f"{current.id}.{ext}").write_bytes(data)
    current.avatar_ext = ext
    current.avatar_updated_at = datetime.now(timezone.utc)
    db.add(current)
    db.commit()
    db.refresh(current)
    return user_public(db, current)


@router.delete("/me/avatar", response_model=UserPublic, summary="移除我的头像")
def delete_my_avatar(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPublic:
    _remove_file(current)
    current.avatar_ext = None
    current.avatar_updated_at = None
    db.add(current)
    db.commit()
    db.refresh(current)
    return user_public(db, current)
