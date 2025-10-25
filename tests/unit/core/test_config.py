"""
設定クラスの単体テスト
"""

from typing import Any
from app.core.config import Settings


class TestConfigDatabaseURI:
    """database_uriプロパティのテスト"""

    def test_database_uri_from_database_url(self, monkeypatch: Any) -> None:
        """DATABASE_URLが設定されている場合、それを優先すること"""
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql://test:test@localhost:5432/testdb"
        )

        # キャッシュクリア
        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = Settings()
        assert settings.database_uri == "postgresql://test:test@localhost:5432/testdb"

        # クリーンアップ
        get_settings.cache_clear()

    def test_database_uri_from_individual_settings(self) -> None:
        """DATABASE_URLがない場合、個別設定から構築すること"""
        from cryptography.fernet import Fernet

        # 直接インスタンス化してテスト（.env読み込みをスキップ）
        settings = Settings(
            _env_file=None,  # .envファイルを読み込まない
            DATABASE_URL=None,
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_HOST="testhost",
            POSTGRES_PORT="5433",
            POSTGRES_DB="testdb",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )

        expected = "postgresql://testuser:testpass@testhost:5433/testdb"
        assert settings.database_uri == expected

    def test_database_uri_none_when_no_config(self) -> None:
        """データベース設定がない場合、Noneを返すこと"""
        from cryptography.fernet import Fernet

        # 直接インスタンス化してテスト（.env読み込みをスキップ）
        settings = Settings(
            _env_file=None,
            DATABASE_URL=None,
            POSTGRES_USER="",
            POSTGRES_PASSWORD="",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )

        assert settings.database_uri is None


class TestConfigHasDatabase:
    """has_databaseプロパティのテスト"""

    def test_has_database_true(self, monkeypatch: Any) -> None:
        """データベース設定がある場合、Trueを返すこと"""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = Settings()
        assert settings.has_database is True

        get_settings.cache_clear()

    def test_has_database_false(self) -> None:
        """データベース設定がない場合、Falseを返すこと"""
        from cryptography.fernet import Fernet

        # 直接インスタンス化してテスト（.env読み込みをスキップ）
        settings = Settings(
            _env_file=None,
            DATABASE_URL=None,
            POSTGRES_USER="",
            POSTGRES_PASSWORD="",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )

        assert settings.has_database is False


class TestConfigIsSupabase:
    """is_supabaseプロパティのテスト"""

    def test_is_supabase_true(self, monkeypatch: Any) -> None:
        """Supabase URLの場合、Trueを返すこと"""
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql://user:pass@db.supabase.co:5432/postgres"
        )

        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = Settings()
        assert settings.is_supabase is True

        get_settings.cache_clear()

    def test_is_supabase_false(self, monkeypatch: Any) -> None:
        """Supabase以外のURLの場合、Falseを返すこと"""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = Settings()
        assert settings.is_supabase is False

        get_settings.cache_clear()

    def test_is_supabase_false_when_no_database(self, monkeypatch: Any) -> None:
        """データベース設定がない場合、Falseを返すこと"""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("POSTGRES_USER", "")
        monkeypatch.setenv("POSTGRES_PASSWORD", "")

        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = Settings()
        assert settings.is_supabase is False

        get_settings.cache_clear()
