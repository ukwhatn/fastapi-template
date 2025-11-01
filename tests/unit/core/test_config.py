"""
設定クラスの単体テスト
"""

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

        expected = (
            "postgresql://testuser:testpass@testhost:5433/testdb?gssencmode=disable"
        )
        assert settings.database_uri == expected


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
