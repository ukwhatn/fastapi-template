"""バックアップコア機能の単体テスト"""

import gzip
import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database.backup.core import create_backup
from app.infrastructure.database.backup.models import BackupData
from app.infrastructure.database.models.session import Session as SessionModel


class TestCreateBackup:
    """create_backup関数のテスト"""

    def test_create_backup_with_data(
        self,
        db_session: Session,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """データがある状態でバックアップが作成されること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # ファイルが作成されていること
        assert backup_file.exists()
        assert backup_file.suffix == ".gz"
        assert backup_file.name.startswith("backup_")

        # ファイルサイズが0より大きいこと
        assert backup_file.stat().st_size > 0

    def test_create_backup_with_empty_table(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        """空のテーブルでもバックアップが作成されること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # ファイルが作成されていること
        assert backup_file.exists()

    def test_create_backup_with_output_dir(
        self,
        db_session: Session,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """指定した出力ディレクトリにバックアップが作成されること"""
        output_dir = tmp_path / "custom_backup_dir"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # 指定したディレクトリにファイルが作成されていること
        assert backup_file.parent == output_dir
        assert backup_file.exists()

    def test_create_backup_file_content(
        self,
        db_session: Session,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """バックアップファイルの内容が正しいこと"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # ファイルを読み込んで解凍
        with gzip.open(backup_file, "rb") as f:
            json_data = f.read().decode("utf-8")

        # JSONをパース
        backup_data = BackupData.model_validate_json(json_data)

        # メタデータの検証
        assert backup_data.metadata.version == "1.0"
        assert isinstance(backup_data.metadata.timestamp, object)
        assert isinstance(backup_data.metadata.migration_version, str)
        assert len(backup_data.metadata.migration_version) > 0
        assert isinstance(backup_data.metadata.database_name, str)
        assert isinstance(backup_data.metadata.database_host, str)

        # テーブルデータの検証
        assert "sessions" in backup_data.tables
        sessions_table = backup_data.tables["sessions"]
        assert sessions_table.row_count == 3
        assert len(sessions_table.data) == 3
        assert len(sessions_table.columns) > 0

        # カラム名の検証
        assert "session_id" in sessions_table.columns
        assert "data" in sessions_table.columns
        assert "expires_at" in sessions_table.columns

    def test_create_backup_compression(
        self,
        db_session: Session,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """バックアップファイルがgzip圧縮されていること"""
        output_dir = tmp_path / "backups"

        # バックアップ作成
        backup_file = create_backup(output_dir=output_dir)

        # gzipファイルとして読み込めること
        try:
            with gzip.open(backup_file, "rb") as f:
                content = f.read()
                # JSON形式としてパースできること
                json.loads(content.decode("utf-8"))
        except Exception as e:
            pytest.fail(f"Failed to decompress or parse backup file: {e}")

    def test_create_backup_default_output_dir(
        self, db_session: Session, sample_session_data: list[SessionModel]
    ) -> None:
        """出力ディレクトリを指定しない場合、./backupsに作成されること"""
        # バックアップ作成
        backup_file = create_backup()

        # デフォルトディレクトリに作成されること
        assert backup_file.parent == Path("./backups")
        assert backup_file.exists()

        # クリーンアップ
        backup_file.unlink()

    def test_create_backup_multiple_times(
        self,
        db_session: Session,
        sample_session_data: list[SessionModel],
        tmp_path: Path,
    ) -> None:
        """複数回バックアップを作成しても異なるファイル名が生成されること"""
        output_dir = tmp_path / "backups"

        # 1回目のバックアップ
        backup_file_1 = create_backup(output_dir=output_dir)

        # 2回目のバックアップ（少し待ってから）
        import time

        time.sleep(1)
        backup_file_2 = create_backup(output_dir=output_dir)

        # 異なるファイル名であること
        assert backup_file_1 != backup_file_2
        assert backup_file_1.exists()
        assert backup_file_2.exists()
