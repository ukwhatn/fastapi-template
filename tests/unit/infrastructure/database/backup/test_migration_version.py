"""マイグレーションバージョン取得機能の単体テスト"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.database.backup.core import get_current_migration_version


class TestGetCurrentMigrationVersion:
    """get_current_migration_version関数のテスト"""

    def test_get_migration_version_success(self, db_session: Session) -> None:
        """マイグレーションバージョンが正しく取得されること"""
        # alembic_versionテーブルにはマイグレーション実行時に既に値が入っている
        version = get_current_migration_version()

        assert isinstance(version, str)
        # 空でない場合は、16進数の文字列
        if version:
            assert len(version) > 0
            # Alembicのリビジョン形式（12文字の16進数）
            assert all(c in "0123456789abcdef" for c in version)

    def test_get_migration_version_when_empty(self, db_session: Session) -> None:
        """
        alembic_versionが空の場合、空文字列が返ること

        Note: 通常の運用では発生しないが、テスト目的で空にした場合の挙動を確認
        """
        # alembic_versionテーブルを一時的に空にする
        db_session.execute(text("DELETE FROM alembic_version"))
        db_session.commit()

        version = get_current_migration_version()

        assert version == ""

    def test_get_migration_version_multiple_times(self, db_session: Session) -> None:
        """複数回呼び出しても同じ結果が返ること"""
        version1 = get_current_migration_version()
        version2 = get_current_migration_version()

        assert version1 == version2
