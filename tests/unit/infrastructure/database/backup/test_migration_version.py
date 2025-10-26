"""マイグレーションバージョン取得機能の単体テスト"""

from sqlalchemy.orm import Session

from app.infrastructure.database.backup.core import get_current_migration_version


class TestGetCurrentMigrationVersion:
    """get_current_migration_version関数のテスト"""

    def test_get_migration_version_success(self, db_session: Session) -> None:
        """マイグレーションバージョンが正しく取得されること"""
        # alembic_versionテーブルにはマイグレーション実行時に既に値が入っている
        version = get_current_migration_version()

        # バージョンが文字列として取得できること
        assert isinstance(version, str)
        # マイグレーション実行済みなので空ではない
        assert len(version) > 0

    def test_get_migration_version_type(self, db_session: Session) -> None:
        """マイグレーションバージョンが常に文字列として返ること"""
        version = get_current_migration_version()

        # 戻り値の型が常に文字列であること
        assert isinstance(version, str)

    def test_get_migration_version_multiple_times(self, db_session: Session) -> None:
        """複数回呼び出しても同じ結果が返ること"""
        version1 = get_current_migration_version()
        version2 = get_current_migration_version()

        assert version1 == version2
