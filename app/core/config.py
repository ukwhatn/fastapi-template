from functools import lru_cache
from typing import Literal, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logging import get_logger

logger = get_logger(__name__)


class Settings(BaseSettings):
    """
    アプリケーション設定
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # 未定義のフィールドを無視
    )

    ENV_MODE: Literal["development", "production", "test"] = "development"

    BACKEND_CORS_ORIGINS: str | list[str] = []

    @classmethod
    @field_validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        if v == "":
            return []
        if v == "*":
            return ["*"]
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    SECURITY_HEADERS: bool = False
    CSP_POLICY: str = (
        "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'"
    )

    API_KEY: str = "default_api_key_change_me_in_production"

    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "main"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"

    @property
    def database_uri(self) -> str:
        """データベース接続URL"""
        # Kerberos設定済み環境だとタイムアウト待ちにハマるので、gssencmode=disableを設定
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?gssencmode=disable"
        )

    @property
    def has_database(self) -> bool:
        """データベース設定有無"""
        return bool(
            self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_HOST
        )

    @property
    def is_supabase(self) -> bool:
        """Supabase使用判定"""
        return "supabase.co" in self.POSTGRES_HOST

    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_EXPIRE: int = 60 * 60 * 24  # 1 day

    SESSION_ENCRYPTION_KEY: str = ""

    @field_validator("SESSION_ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """暗号化キー検証"""
        if not v:
            logger.warning(
                "SESSION_ENCRYPTION_KEY is not set. Session encryption disabled."
            )
            return ""

        try:
            from cryptography.fernet import Fernet

            Fernet(v.encode())
        except Exception:
            raise ValueError(
                'Invalid SESSION_ENCRYPTION_KEY format. Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )

        return v

    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0

    @classmethod
    @field_validator("SENTRY_DSN")
    def sentry_dsn_can_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v

    NEW_RELIC_LICENSE_KEY: Optional[str] = None
    NEW_RELIC_APP_NAME: str = "FastAPI Template"
    NEW_RELIC_HIGH_SECURITY: bool = False
    NEW_RELIC_MONITOR_MODE: bool = True

    BACKUP_SCHEDULE: Optional[str] = None  # cron形式 (例: "0 3 * * *")
    BACKUP_RETENTION_DAYS: int = 7

    S3_ENDPOINT: Optional[str] = None
    S3_BUCKET: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: Optional[str] = None

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
