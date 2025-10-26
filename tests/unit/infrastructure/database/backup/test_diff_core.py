"""差分計算機能の単体テスト"""

from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.backup.core import calculate_diff, create_backup
from app.infrastructure.database.models.session import Session as SessionModel


class TestCalculateDiff:
    """calculate_diff関数のテスト"""

    def test_calculate_diff_no_changes(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """データに変更がない場合、差分が0になること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # 差分計算
        diff_summary = calculate_diff(backup_file)

        # 差分が0であること
        assert diff_summary.total_diff == 0
        assert diff_summary.total_current_rows == diff_summary.total_backup_rows
        assert "sessions" in diff_summary.tables
        assert diff_summary.tables["sessions"].diff == 0

    def test_calculate_diff_with_added_rows(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """バックアップ後にデータが追加された場合、差分が負になること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # データを追加
        TestSessionLocal = sessionmaker(bind=test_engine)
        db = TestSessionLocal()
        try:
            from datetime import UTC, datetime

            new_session = SessionModel(
                session_id="test_session_4",
                data="encrypted_data_4",
                expires_at=datetime.now(UTC),
                fingerprint="fingerprint_4",
                csrf_token="csrf_token_4",
            )
            db.add(new_session)
            db.commit()

            # 差分計算
            diff_summary = calculate_diff(backup_file)

            # 差分が負（現在の方が多い）であること
            assert diff_summary.total_diff == -1
            assert diff_summary.total_current_rows == diff_summary.total_backup_rows + 1
            assert diff_summary.tables["sessions"].diff == -1
            assert diff_summary.tables["sessions"].current_rows == 4
            assert diff_summary.tables["sessions"].backup_rows == 3

        finally:
            # クリーンアップ
            db.query(SessionModel).filter(
                SessionModel.session_id == "test_session_4"
            ).delete()
            db.commit()
            db.close()

    def test_calculate_diff_with_deleted_rows(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """バックアップ後にデータが削除された場合、差分が正になること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # データを削除
        TestSessionLocal = sessionmaker(bind=test_engine)
        db = TestSessionLocal()
        try:
            db.query(SessionModel).filter(
                SessionModel.session_id == "test_session_1"
            ).delete()
            db.commit()

            # 差分計算
            diff_summary = calculate_diff(backup_file)

            # 差分が正（バックアップの方が多い）であること
            assert diff_summary.total_diff == 1
            assert diff_summary.total_current_rows == diff_summary.total_backup_rows - 1
            assert diff_summary.tables["sessions"].diff == 1
            assert diff_summary.tables["sessions"].current_rows == 2
            assert diff_summary.tables["sessions"].backup_rows == 3

        finally:
            db.close()

    def test_calculate_diff_with_empty_current_table(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """現在のテーブルが空の場合、差分が正になること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # 全データを削除
        TestSessionLocal = sessionmaker(bind=test_engine)
        db = TestSessionLocal()
        try:
            db.query(SessionModel).delete()
            db.commit()

            # 差分計算
            diff_summary = calculate_diff(backup_file)

            # 差分が正（バックアップの方が多い）であること
            assert diff_summary.total_diff == 3
            assert diff_summary.total_current_rows == 0
            assert diff_summary.total_backup_rows == 3
            assert diff_summary.tables["sessions"].diff == 3
            assert diff_summary.tables["sessions"].current_rows == 0
            assert diff_summary.tables["sessions"].backup_rows == 3

        finally:
            db.close()

    def test_calculate_diff_nonexistent_backup_file(
        self, test_engine: Engine, tmp_path: Path
    ) -> None:
        """存在しないバックアップファイルの場合、RuntimeErrorが発生すること"""
        nonexistent_file = tmp_path / "nonexistent.backup.gz"

        with pytest.raises(RuntimeError, match="Backup file not found"):
            calculate_diff(nonexistent_file)

    def test_calculate_diff_invalid_backup_file(
        self, test_engine: Engine, tmp_path: Path
    ) -> None:
        """不正なバックアップファイルの場合、RuntimeErrorが発生すること"""
        invalid_file = tmp_path / "invalid.backup.gz"
        invalid_file.write_text("invalid data")

        with pytest.raises(RuntimeError):
            calculate_diff(invalid_file)

    def test_calculate_diff_summary_structure(
        self,
        test_engine: Engine,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """差分サマリの構造が正しいこと"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # 差分計算
        diff_summary = calculate_diff(backup_file)

        # 構造の検証
        assert hasattr(diff_summary, "tables")
        assert hasattr(diff_summary, "total_current_rows")
        assert hasattr(diff_summary, "total_backup_rows")
        assert hasattr(diff_summary, "total_diff")

        # テーブル差分の構造
        for table_name, table_diff in diff_summary.tables.items():
            assert hasattr(table_diff, "current_rows")
            assert hasattr(table_diff, "backup_rows")
            assert hasattr(table_diff, "diff")
            assert isinstance(table_diff.current_rows, int)
            assert isinstance(table_diff.backup_rows, int)
            assert isinstance(table_diff.diff, int)
