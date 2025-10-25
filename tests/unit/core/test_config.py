"""
設定クラスの単体テスト
"""

from typing import Any
from app.core.config import Settings


class TestConfigDatabaseURI:
    """database_uriプロパティのテスト"""

    def test_database_uri_from_individual_settings(self) -> None:
        """個別設定から接続URLを構築すること"""
        from cryptography.fernet import Fernet

        # 直接インスタンス化してテスト（.env読み込みをスキップ）
        settings = Settings(
            _env_file=None,  # .envファイルを読み込まない
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_HOST="testhost",
            POSTGRES_PORT="5433",
            POSTGRES_DB="testdb",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )

        expected = "postgresql://testuser:testpass@testhost:5433/testdb"
        assert settings.database_uri == expected

    def test_database_uri_always_returns_string(self) -> None:
        """データベース設定が空でも文字列を返すこと（構築は可能）"""
        from cryptography.fernet import Fernet

        # 直接インスタンス化してテスト（.env読み込みをスキップ）
        settings = Settings(
            _env_file=None,
            POSTGRES_USER="",
            POSTGRES_PASSWORD="",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )

        # 空の設定でも文字列が構築される（デフォルト値が使用される）
        assert isinstance(settings.database_uri, str)
        assert "postgresql://" in settings.database_uri


class TestConfigHasDatabase:
    """has_databaseプロパティのテスト"""

    def test_has_database_true(self) -> None:
        """データベース設定がある場合、Trueを返すこと"""
        from cryptography.fernet import Fernet

        settings = Settings(
            _env_file=None,
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_HOST="localhost",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )
        assert settings.has_database is True

    def test_has_database_false(self) -> None:
        """データベース設定がない場合、Falseを返すこと"""
        from cryptography.fernet import Fernet

        # 直接インスタンス化してテスト（.env読み込みをスキップ）
        settings = Settings(
            _env_file=None,
            POSTGRES_USER="",
            POSTGRES_PASSWORD="",
            POSTGRES_HOST="",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )

        assert settings.has_database is False


class TestConfigIsSupabase:
    """is_supabaseプロパティのテスト"""

    def test_is_supabase_true(self) -> None:
        """Supabase HOSTの場合、Trueを返すこと"""
        from cryptography.fernet import Fernet

        settings = Settings(
            _env_file=None,
            POSTGRES_HOST="db.abcdefghijklmnop.supabase.co",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )
        assert settings.is_supabase is True

    def test_is_supabase_false(self) -> None:
        """Supabase以外のHOSTの場合、Falseを返すこと"""
        from cryptography.fernet import Fernet

        settings = Settings(
            _env_file=None,
            POSTGRES_HOST="localhost",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )
        assert settings.is_supabase is False

    def test_is_supabase_false_when_host_is_db(self) -> None:
        """POSTGRES_HOSTがdbの場合、Falseを返すこと"""
        from cryptography.fernet import Fernet

        settings = Settings(
            _env_file=None,
            POSTGRES_HOST="db",
            SESSION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )
        assert settings.is_supabase is False
