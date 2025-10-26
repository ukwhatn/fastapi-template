"""バックアップデータモデルの単体テスト"""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.infrastructure.database.backup.models import (
    BackupData,
    BackupMetadata,
    DiffSummary,
    RestoreResult,
    TableBackup,
    TableDiff,
)


class TestBackupMetadata:
    """BackupMetadataモデルのテスト"""

    def test_create_backup_metadata(self) -> None:
        """BackupMetadataが正しく作成されること"""
        now = datetime.now()
        metadata = BackupMetadata(
            timestamp=now,
            migration_version="abc123def456",
            database_name="test_db",
            database_host="localhost",
        )

        assert metadata.version == "1.0"
        assert metadata.timestamp == now
        assert metadata.migration_version == "abc123def456"
        assert metadata.database_name == "test_db"
        assert metadata.database_host == "localhost"

    def test_backup_metadata_with_empty_migration_version(self) -> None:
        """マイグレーションバージョンが空文字列でも作成できること"""
        metadata = BackupMetadata(
            timestamp=datetime.now(),
            migration_version="",
            database_name="test_db",
            database_host="localhost",
        )

        assert metadata.migration_version == ""

    def test_backup_metadata_serialization(self) -> None:
        """BackupMetadataがJSON化できること"""
        now = datetime.now()
        metadata = BackupMetadata(
            timestamp=now,
            migration_version="abc123",
            database_name="test_db",
            database_host="localhost",
        )

        json_str = metadata.model_dump_json()
        assert isinstance(json_str, str)

        # JSON文字列をパースして検証
        data = json.loads(json_str)
        assert data["version"] == "1.0"
        assert data["migration_version"] == "abc123"
        assert data["database_name"] == "test_db"

    def test_backup_metadata_deserialization(self) -> None:
        """JSONからBackupMetadataを復元できること"""
        json_data = {
            "version": "1.0",
            "timestamp": "2025-01-01T00:00:00",
            "migration_version": "abc123",
            "database_name": "test_db",
            "database_host": "localhost",
        }

        metadata = BackupMetadata.model_validate(json_data)
        assert metadata.version == "1.0"
        assert metadata.migration_version == "abc123"
        assert metadata.database_name == "test_db"


class TestTableBackup:
    """TableBackupモデルのテスト"""

    def test_create_table_backup(self) -> None:
        """TableBackupが正しく作成されること"""
        table_backup = TableBackup(
            row_count=3,
            columns=["id", "name", "email"],
            data=[
                [1, "Alice", "alice@example.com"],
                [2, "Bob", "bob@example.com"],
                [3, "Charlie", "charlie@example.com"],
            ],
        )

        assert table_backup.row_count == 3
        assert len(table_backup.columns) == 3
        assert len(table_backup.data) == 3
        assert table_backup.data[0] == [1, "Alice", "alice@example.com"]

    def test_create_empty_table_backup(self) -> None:
        """空のテーブルバックアップが作成できること"""
        table_backup = TableBackup(row_count=0, columns=["id", "name"], data=[])

        assert table_backup.row_count == 0
        assert len(table_backup.data) == 0

    def test_table_backup_serialization(self) -> None:
        """TableBackupがJSON化できること"""
        table_backup = TableBackup(
            row_count=2, columns=["id", "value"], data=[[1, "test"], [2, "data"]]
        )

        json_str = table_backup.model_dump_json()
        data = json.loads(json_str)

        assert data["row_count"] == 2
        assert data["columns"] == ["id", "value"]
        assert len(data["data"]) == 2


class TestBackupData:
    """BackupDataモデルのテスト"""

    def test_create_backup_data(self) -> None:
        """BackupDataが正しく作成されること"""
        metadata = BackupMetadata(
            timestamp=datetime.now(),
            migration_version="abc123",
            database_name="test_db",
            database_host="localhost",
        )

        tables = {
            "users": TableBackup(
                row_count=2, columns=["id", "name"], data=[[1, "Alice"], [2, "Bob"]]
            ),
            "posts": TableBackup(
                row_count=1, columns=["id", "title"], data=[[1, "Hello"]]
            ),
        }

        backup_data = BackupData(metadata=metadata, tables=tables)

        assert backup_data.metadata.database_name == "test_db"
        assert len(backup_data.tables) == 2
        assert "users" in backup_data.tables
        assert "posts" in backup_data.tables
        assert backup_data.tables["users"].row_count == 2

    def test_backup_data_round_trip(self) -> None:
        """BackupDataのシリアライズ→デシリアライズが正しく動作すること"""
        metadata = BackupMetadata(
            timestamp=datetime.now(),
            migration_version="abc123",
            database_name="test_db",
            database_host="localhost",
        )

        tables = {
            "users": TableBackup(
                row_count=1, columns=["id", "name"], data=[[1, "Alice"]]
            )
        }

        original = BackupData(metadata=metadata, tables=tables)

        # JSON化
        json_str = original.model_dump_json()

        # 復元
        restored = BackupData.model_validate_json(json_str)

        assert restored.metadata.migration_version == "abc123"
        assert len(restored.tables) == 1
        assert restored.tables["users"].row_count == 1
        assert restored.tables["users"].data[0] == [1, "Alice"]


class TestTableDiff:
    """TableDiffモデルのテスト"""

    def test_create_table_diff(self) -> None:
        """TableDiffが正しく作成されること"""
        table_diff = TableDiff(current_rows=10, backup_rows=8, diff=-2)

        assert table_diff.current_rows == 10
        assert table_diff.backup_rows == 8
        assert table_diff.diff == -2

    def test_table_diff_positive(self) -> None:
        """正のdiffが正しく表現されること"""
        table_diff = TableDiff(current_rows=5, backup_rows=10, diff=5)

        assert table_diff.diff == 5
        assert table_diff.backup_rows > table_diff.current_rows

    def test_table_diff_zero(self) -> None:
        """diff=0が正しく表現されること"""
        table_diff = TableDiff(current_rows=5, backup_rows=5, diff=0)

        assert table_diff.diff == 0
        assert table_diff.current_rows == table_diff.backup_rows


class TestDiffSummary:
    """DiffSummaryモデルのテスト"""

    def test_create_diff_summary(self) -> None:
        """DiffSummaryが正しく作成されること"""
        tables = {
            "users": TableDiff(current_rows=10, backup_rows=8, diff=-2),
            "posts": TableDiff(current_rows=5, backup_rows=7, diff=2),
        }

        diff_summary = DiffSummary(
            tables=tables, total_current_rows=15, total_backup_rows=15, total_diff=0
        )

        assert len(diff_summary.tables) == 2
        assert diff_summary.total_current_rows == 15
        assert diff_summary.total_backup_rows == 15
        assert diff_summary.total_diff == 0

    def test_diff_summary_with_total_diff(self) -> None:
        """総差分が正しく計算されること"""
        tables = {"users": TableDiff(current_rows=5, backup_rows=10, diff=5)}

        diff_summary = DiffSummary(
            tables=tables, total_current_rows=5, total_backup_rows=10, total_diff=5
        )

        assert diff_summary.total_diff == 5


class TestRestoreResult:
    """RestoreResultモデルのテスト"""

    def test_create_restore_result_success(self) -> None:
        """成功したRestoreResultが作成されること"""
        result = RestoreResult(
            success=True,
            message="Restored 2 tables with 10 rows",
            restored_tables=2,
            restored_rows=10,
        )

        assert result.success is True
        assert "Restored" in result.message
        assert result.restored_tables == 2
        assert result.restored_rows == 10
        assert result.diff_summary is None

    def test_create_restore_result_failure(self) -> None:
        """失敗したRestoreResultが作成されること"""
        result = RestoreResult(
            success=False, message="Restore failed: connection error"
        )

        assert result.success is False
        assert "failed" in result.message
        assert result.restored_tables == 0
        assert result.restored_rows == 0

    def test_restore_result_with_diff_summary(self) -> None:
        """diff_summaryを含むRestoreResultが作成されること"""
        diff_summary = DiffSummary(
            tables={"users": TableDiff(current_rows=5, backup_rows=10, diff=5)},
            total_current_rows=5,
            total_backup_rows=10,
            total_diff=5,
        )

        result = RestoreResult(
            success=True,
            message="Restored successfully",
            diff_summary=diff_summary,
            restored_tables=1,
            restored_rows=10,
        )

        assert result.diff_summary is not None
        assert result.diff_summary.total_diff == 5
        assert len(result.diff_summary.tables) == 1


class TestModelValidation:
    """モデルのバリデーションテスト"""

    def test_backup_metadata_missing_required_field(self) -> None:
        """必須フィールドが欠けている場合にValidationErrorが発生すること"""
        with pytest.raises(ValidationError):
            BackupMetadata(  # type: ignore[call-arg]
                timestamp=datetime.now(),
                migration_version="abc123",
                # database_name is missing
                database_host="localhost",
            )

    def test_table_backup_invalid_data_type(self) -> None:
        """不正なデータ型でValidationErrorが発生すること"""
        with pytest.raises(ValidationError):
            TableBackup(row_count="invalid", columns=["id"], data=[[1]])
