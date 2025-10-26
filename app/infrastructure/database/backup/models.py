"""バックアップデータのモデル定義"""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class BackupMetadata(BaseModel):
    """
    バックアップのメタデータ

    Attributes:
        version: バックアップフォーマットのバージョン
        timestamp: バックアップ作成日時
        migration_version: Alembicマイグレーションのリビジョン
        database_name: データベース名
        database_host: データベースホスト
    """

    version: str = Field(
        default="1.0", description="バックアップフォーマットのバージョン"
    )
    timestamp: datetime = Field(description="バックアップ作成日時")
    migration_version: str = Field(description="Alembicマイグレーションのリビジョン")
    database_name: str = Field(description="データベース名")
    database_host: str = Field(description="データベースホスト")


class TableBackup(BaseModel):
    """
    テーブルのバックアップデータ

    Attributes:
        row_count: 行数
        columns: カラム名のリスト
        data: 行データのリスト（各行はカラムの値のリスト）
    """

    row_count: int = Field(description="行数")
    columns: List[str] = Field(description="カラム名のリスト")
    data: List[List[Any]] = Field(description="行データのリスト")


class BackupData(BaseModel):
    """
    バックアップ全体のデータ構造

    Attributes:
        metadata: メタデータ
        tables: テーブル名をキー、TableBackupを値とする辞書
    """

    metadata: BackupMetadata = Field(description="メタデータ")
    tables: Dict[str, TableBackup] = Field(description="テーブルデータ")


class TableDiff(BaseModel):
    """
    テーブルごとの差分情報

    Attributes:
        current_rows: 現在の行数
        backup_rows: バックアップの行数
        diff: 差分（バックアップ - 現在）
    """

    current_rows: int = Field(description="現在の行数")
    backup_rows: int = Field(description="バックアップの行数")
    diff: int = Field(description="差分（バックアップ - 現在）")


class DiffSummary(BaseModel):
    """
    バックアップとの差分サマリ

    Attributes:
        tables: テーブル名をキー、TableDiffを値とする辞書
        total_current_rows: 現在の総行数
        total_backup_rows: バックアップの総行数
        total_diff: 総差分
    """

    tables: Dict[str, TableDiff] = Field(description="テーブルごとの差分")
    total_current_rows: int = Field(description="現在の総行数")
    total_backup_rows: int = Field(description="バックアップの総行数")
    total_diff: int = Field(description="総差分")


class RestoreResult(BaseModel):
    """
    リストア結果

    Attributes:
        success: 成功フラグ
        message: メッセージ
        diff_summary: 差分サマリ（リストア前に計算された場合）
        restored_tables: リストアされたテーブル数
        restored_rows: リストアされた総行数
    """

    success: bool = Field(description="成功フラグ")
    message: str = Field(description="メッセージ")
    diff_summary: DiffSummary | None = Field(
        default=None, description="差分サマリ（リストア前に計算された場合）"
    )
    restored_tables: int = Field(default=0, description="リストアされたテーブル数")
    restored_rows: int = Field(default=0, description="リストアされた総行数")
