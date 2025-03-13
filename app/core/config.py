import secrets
from functools import lru_cache
from typing import List, Literal, Optional, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    アプリケーション設定
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # 環境設定
    ENV_MODE: Literal["development", "production", "test"] = "development"

    # APIパス設定
    API_V1_STR: str = "/v1"
    SYSTEM_STR: str = "/system"

    # セキュリティ設定
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # CORS設定
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # セキュリティヘッダー設定
    SECURITY_HEADERS: bool = True
    CSP_POLICY: str = (
        "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'"
    )

    # レート制限設定
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD_SECONDS: int = 60

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # データベース設定
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE: int = 3600

    @property
    def DATABASE_URI(self) -> str:
        """
        データベース接続URLを取得
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis設定
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_USE_SSL: bool = False
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_EXPIRE: int = 60 * 60 * 24  # 1 day
    SESSION_SECURE: bool = False
    SESSION_HTTPONLY: bool = True
    SESSION_SAMESITE: str = "lax"

    # Sentry設定
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0
    SENTRY_ENVIRONMENT: str = "development"

    @field_validator("SENTRY_DSN")
    @classmethod
    def sentry_dsn_can_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v

    # ロギング設定
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"

    @property
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.ENV_MODE == "development"

    @property
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.ENV_MODE == "production"

    @property
    def is_test(self) -> bool:
        """テスト環境かどうか"""
        return self.ENV_MODE == "test"


@lru_cache
def get_settings() -> Settings:
    """
    アプリケーション設定を取得（キャッシュ）
    """
    return Settings()
