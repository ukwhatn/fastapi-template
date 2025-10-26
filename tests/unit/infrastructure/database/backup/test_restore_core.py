"""リストア機能の単体テスト"""

from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.backup.core import create_backup, restore_backup
from app.infrastructure.database.models.session import Session as SessionModel


class TestRestoreBackup:
    """restore_backup関数のテスト"""

    def test_restore_backup_success(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """バックアップからのリストアが成功すること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # データを削除
        TestSessionLocal = sessionmaker(bind=test_engine)
        db = TestSessionLocal()
        try:
            db.query(SessionModel).delete()
            db.commit()

        finally:
            db.close()

        # リストア実行（セッションをクローズ後に実行）
        result = restore_backup(backup_file)

        # 成功していること
        assert result.success is True
        assert result.restored_tables == 1
        assert result.restored_rows == 3
        assert "Restored" in result.message

        # 新しいセッションで検証
        db = TestSessionLocal()
        try:
            # データが復元されていること
            count = db.query(SessionModel).count()
            assert count == 3

        finally:
            db.close()

    def test_restore_backup_with_diff(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """diff表示オプション付きでリストアできること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # データを削除
        TestSessionLocal = sessionmaker(bind=test_engine)
        db = TestSessionLocal()
        try:
            db.query(SessionModel).delete()
            db.commit()

        finally:
            db.close()

        # diff付きでリストア実行（セッションをクローズ後に実行）
        result = restore_backup(backup_file, show_diff=True)

        # 成功していること
        assert result.success is True
        assert result.diff_summary is not None
        assert result.diff_summary.total_diff == 3

    def test_restore_backup_without_diff(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """diff表示なしでリストアできること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # diff無しでリストア実行
        result = restore_backup(backup_file, show_diff=False)

        # 成功していること
        assert result.success is True
        assert result.diff_summary is None

    def test_restore_backup_overwrites_existing_data(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """既存データが上書きされること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # データを追加
        TestSessionLocal = sessionmaker(bind=test_engine)
        db = TestSessionLocal()
        try:
            from datetime import UTC, datetime

            new_session = SessionModel(
                session_id="test_session_new",
                data="encrypted_data_new",
                expires_at=datetime.now(UTC),
                fingerprint="fingerprint_new",
                csrf_token="csrf_token_new",
            )
            db.add(new_session)
            db.commit()

            # 現在のデータ数を確認
            count_before = db.query(SessionModel).count()
            assert count_before == 4  # 3 + 1

        finally:
            db.close()

        # リストア実行（セッションをクローズ後に実行）
        result = restore_backup(backup_file, show_diff=False)

        # 成功していること
        assert result.success is True

        # 新しいセッションで検証
        db = TestSessionLocal()
        try:
            # データがバックアップの状態に戻っていること
            count_after = db.query(SessionModel).count()
            assert count_after == 3

            # 新しく追加したデータは削除されていること
            new_session_exists = (
                db.query(SessionModel)
                .filter(SessionModel.session_id == "test_session_new")
                .first()
            )
            assert new_session_exists is None

        finally:
            db.close()

    def test_restore_backup_nonexistent_file(
        self, test_engine: Engine, tmp_path: Path
    ) -> None:
        """存在しないバックアップファイルの場合、失敗すること"""
        nonexistent_file = tmp_path / "nonexistent.backup.gz"

        result = restore_backup(nonexistent_file, show_diff=False)

        # 失敗していること
        assert result.success is False
        assert "failed" in result.message.lower()
        assert result.restored_tables == 0
        assert result.restored_rows == 0

    def test_restore_backup_invalid_file(
        self, test_engine: Engine, tmp_path: Path
    ) -> None:
        """不正なバックアップファイルの場合、失敗すること"""
        invalid_file = tmp_path / "invalid.backup.gz"
        invalid_file.write_text("invalid data")

        result = restore_backup(invalid_file, show_diff=False)

        # 失敗していること
        assert result.success is False
        assert result.restored_tables == 0
        assert result.restored_rows == 0

    def test_restore_backup_empty_table(
        self, test_engine: Engine, tmp_path: Path
    ) -> None:
        """空のテーブルをリストアできること"""
        output_dir = tmp_path / "backups"

        # 空の状態でバックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # リストア実行
        result = restore_backup(backup_file, show_diff=False)

        # 成功していること（空でも成功）
        assert result.success is True
        assert result.restored_rows == 0

    def test_restore_result_structure(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """RestoreResultの構造が正しいこと"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # リストア実行
        result = restore_backup(backup_file)

        # 構造の検証
        assert hasattr(result, "success")
        assert hasattr(result, "message")
        assert hasattr(result, "diff_summary")
        assert hasattr(result, "restored_tables")
        assert hasattr(result, "restored_rows")

        assert isinstance(result.success, bool)
        assert isinstance(result.message, str)
        assert isinstance(result.restored_tables, int)
        assert isinstance(result.restored_rows, int)
