from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "信息集成管理系统"
    API_V1_PREFIX: str = "/api"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    DATABASE_URL: str = "sqlite:///./app.db"

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # ---- 认证后端(按顺序尝试) ----
    AUTH_BACKENDS: list[str] = ["local", "ldap"]

    # ---- AD / LDAP 配置 ----
    LDAP_ENABLED: bool = False
    LDAP_SERVER: str = "ldaps://localhost"  # 生产必须 ldaps://
    LDAP_BIND_DN: str = ""  # 用于搜索的服务账号
    LDAP_BIND_PASSWORD: str = ""
    LDAP_BASE_DN: str = ""
    LDAP_CONNECT_TIMEOUT: int = 5
    LDAP_AUTO_PROVISION: bool = True
    # AD 组 DN(或组 CN) -> 本地角色 code
    LDAP_GROUP_ROLE_MAP: dict[str, str] = {}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
