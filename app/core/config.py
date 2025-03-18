from functools import lru_cache
from typing import List, Literal, Optional, Union

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

    # CORS設定
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = []

    @classmethod
    @field_validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        # 設定されていない場合は空リストを返す
        if v == "":
            return []
        # "*"が設定されている場合は全てのオリジンを許可
        if v == "*":
            return ["*"]
        # カンマ区切りの文字列をリストに変換
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        # リストの場合はそのまま返す
        if isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # セキュリティヘッダー設定
    SECURITY_HEADERS: bool = False
    CSP_POLICY: str = (
        "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'"
    )

    # APIキー設定
    API_KEY: str = "default_api_key_change_me_in_production"

    # データベース設定
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "main"
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

    @classmethod
    @field_validator("SENTRY_DSN")
    def sentry_dsn_can_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v

    # New Relic設定
    NEW_RELIC_LICENSE_KEY: Optional[str] = None
    NEW_RELIC_APP_NAME: str = "FastAPI Template"
    NEW_RELIC_HIGH_SECURITY: bool = False
    NEW_RELIC_MONITOR_MODE: bool = True

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
