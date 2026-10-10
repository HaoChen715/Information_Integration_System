from functools import lru_cache
from typing import Optional

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
    LDAP_USE_STARTTLS: bool = False  # ldap:// + StartTLS
    LDAP_TLS_INSECURE: bool = False  # 跳过证书校验(仅测试)
    LDAP_CA_CERT: Optional[str] = None  # 内网 CA 证书路径
    # AD 组 DN(或组 CN) -> 本地角色 code
    LDAP_GROUP_ROLE_MAP: dict[str, str] = {}

    # ---- OIDC 统一身份认证 ----
    OIDC_ENABLED: bool = False
    OIDC_ISSUER: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""  # 机密客户端才需要
    OIDC_SCOPES: str = "openid profile email groups"
    OIDC_REDIRECT_URI: str = ""  # 后端回调地址,须与 IdP 注册一致
    OIDC_POST_LOGIN_REDIRECT: str = "/oidc-callback"  # 前端接收 token 的路由
    OIDC_USERNAME_CLAIM: str = "preferred_username"
    OIDC_NAME_CLAIM: str = "name"
    OIDC_EMAIL_CLAIM: str = "email"
    OIDC_GROUPS_CLAIM: str = "groups"
    OIDC_GROUP_ROLE_MAP: dict[str, str] = {}
    OIDC_VERIFY_SSL: bool = True
    OIDC_CA_CERT: Optional[str] = None  # 内网 CA 证书路径(优先于 VERIFY_SSL)
    OIDC_COOKIE_SECURE: bool = False

    # ---- 首次启动引导管理员(可选,仅当该用户不存在时创建) ----
    BOOTSTRAP_ADMIN_USERNAME: Optional[str] = None
    BOOTSTRAP_ADMIN_PASSWORD: Optional[str] = None
    BOOTSTRAP_ADMIN_EMAIL: Optional[str] = None

    # ---- 在线用户统计 ----
    ONLINE_WINDOW_MINUTES: int = 15  # 最近活跃在此窗口内视为在线
    LAST_SEEN_UPDATE_SECONDS: int = 60  # 活跃时间写入的最小间隔

    # ---- 头像 ----
    AVATAR_DIR: str = "./data/avatars"
    AVATAR_MAX_MB: int = 2

    # ---- Baserow 数据源 ----
    BASEROW_ENABLED: bool = False
    # 单源配置(兼容旧配置;若配置了 BASEROW_SOURCES 则忽略)
    BASEROW_URL: str = "http://192.168.31.253"
    BASEROW_TOKEN: str = ""  # 数据库令牌
    # 数据集名称 -> Baserow 表 ID
    BASEROW_TABLES: dict[str, str] = {}
    # 按部门过滤所用的字段名(留空则不过滤)
    BASEROW_DEPARTMENT_FIELD: str = "部门"
    # 多源配置:每个源对应一个 Baserow 工作区(独立令牌)
    # {"源名": {"url": "...", "token": "...", "tables": {"数据集": "表ID"}, "department_field": "部门"}}
    BASEROW_SOURCES: dict[str, dict] = {}
    # 用户自动发现模式:配置 Baserow 用户账号后,自动列出所有库/表(优先级高于上面两种)
    BASEROW_USER_EMAIL: str = ""
    BASEROW_USER_PASSWORD: str = ""
    # 仅暴露这些工作区(留空=全部)
    BASEROW_WORKSPACES: list[str] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
