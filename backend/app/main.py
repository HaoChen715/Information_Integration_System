from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, departments, oidc, records, users
from app.core.avatars import avatar_dir
from app.core.config import settings
from app.core.permissions import seed_default_roles, seed_permissions
from app.crud import user as user_crud
from app.db.base import Base
from app.db.migrate import ensure_columns
from app.db.session import SessionLocal, engine
import app.models  # noqa: F401  确保模型注册到 metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_columns(engine)
    avatar_dir()
    db = SessionLocal()
    try:
        seed_permissions(db)
        seed_default_roles(db)
        user_crud.ensure_bootstrap_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.6.1",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(oidc.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(records.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(departments.router, prefix=settings.API_V1_PREFIX)


@app.get("/api/health", tags=["系统"], summary="健康检查")
def health() -> dict[str, str]:
    return {"status": "ok"}
