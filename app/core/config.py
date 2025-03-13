from functools import lru_cache
from typing import Literal, Optional

from pydantic import field_validator
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
    SECRET_KEY: str = "CHANGE_THIS_TO_SECURE_KEY"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # データベース設定
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"

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
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_EXPIRE: int = 60 * 60 * 24  # 1 day

    # Sentry設定
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0

    @field_validator("SENTRY_DSN")
    @classmethod
    def sentry_dsn_can_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    """
    アプリケーション設定を取得（キャッシュ）
    """
    return Settings()