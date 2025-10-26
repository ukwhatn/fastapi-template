"""データベースバックアップ・リストアのコアロジック"""

import gzip
from datetime import datetime
from pathlib import Path
from typing import Any

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

from .models import BackupData, BackupMetadata, DiffSummary, TableBackup, TableDiff

logger = get_logger(__name__)


def _create_alembic_config(settings: Settings) -> Config:
    """
    Alembic設定オブジェクトを作成する

    Args:
        settings: アプリケーション設定

    Returns:
        Config: Alembic設定オブジェクト
    """
    alembic_cfg = Config()

    # スクリプトディレクトリの絶対パスを設定
    script_location = (Path(__file__).parent.parent / "alembic").resolve()
    alembic_cfg.set_main_option("script_location", str(script_location))

    # データベースURLを設定
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_uri)

    return alembic_cfg


def get_current_migration_version() -> str:
    """
    現在のマイグレーションバージョンを取得する

    Returns:
        str: 現在のAlembicリビジョンID（マイグレーション未適用の場合は空文字列）

    Raises:
        RuntimeError: マイグレーションバージョンの取得に失敗した場合
    """
    try:
        settings = get_settings()

        # データベースから現在のリビジョンを取得
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_uri)
        with engine.connect() as conn:
            # alembic_versionテーブルから現在のバージョンを取得
            result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()

            if result:
                return result[0]
            else:
                logger.warning("No migration version found in database")
                return ""

    except Exception as e:
        logger.error(f"Failed to get migration version: {e}")
        raise RuntimeError(f"Failed to get migration version: {e}") from e


def _serialize_value(value: Any) -> Any:
    """
    データベースの値をJSON化可能な形式に変換する

    Args:
        value: データベースの値

    Returns:
        JSON化可能な値
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        # バイナリデータはbase64エンコード
        import base64

        return {"__type__": "bytes", "data": base64.b64encode(value).decode("utf-8")}
    # その他はそのまま返す（int, str, float, bool等）
    return value


def create_backup(output_dir: Path | None = None) -> Path:
    """
    データベースのバックアップを作成する

    Args:
        output_dir: 出力先ディレクトリ（Noneの場合は ./backups）

    Returns:
        Path: 作成されたバックアップファイルのパス

    Raises:
        RuntimeError: バックアップの作成に失敗した場合
    """
    try:
        settings = get_settings()

        # 出力先ディレクトリの確保
        if output_dir is None:
            output_dir = Path("./backups")
        output_dir.mkdir(parents=True, exist_ok=True)

        # マイグレーションバージョンを取得
        migration_version = get_current_migration_version()

        # メタデータ作成
        metadata = BackupMetadata(
            timestamp=datetime.now(),
            migration_version=migration_version,
            database_name=settings.POSTGRES_DB,
            database_host=settings.POSTGRES_HOST,
        )

        logger.info("Creating database backup...")
        logger.info(f"Migration version: {migration_version}")

        # データベースに接続
        engine = create_engine(settings.database_uri)
        inspector = inspect(engine)

        # 全テーブルのデータを取得
        tables_data: dict[str, TableBackup] = {}
        total_rows = 0
        total_size_bytes = 0

        table_names = inspector.get_table_names()

        for table_name in table_names:
            # alembic_versionテーブルはスキップ（メタデータに含まれているため）
            if table_name == "alembic_version":
                continue

            with engine.connect() as conn:
                # カラム情報を取得
                columns = [col["name"] for col in inspector.get_columns(table_name)]

                # 全行を取得
                result = conn.execute(text(f"SELECT * FROM {table_name}"))
                rows = result.fetchall()

                # データをシリアライズ
                serialized_rows = [
                    [_serialize_value(val) for val in row] for row in rows
                ]

                # テーブルデータを格納
                table_backup = TableBackup(
                    row_count=len(rows), columns=columns, data=serialized_rows
                )
                tables_data[table_name] = table_backup

                # 統計情報をログ出力
                table_json = table_backup.model_dump_json()
                table_size_kb = len(table_json.encode("utf-8")) / 1024
                logger.info(
                    f"- {table_name}: {len(rows)} rows ({table_size_kb:.2f} KB)"
                )

                total_rows += len(rows)
                total_size_bytes += len(table_json.encode("utf-8"))

        # バックアップデータを作成
        backup_data = BackupData(metadata=metadata, tables=tables_data)

        # JSON化
        json_data = backup_data.model_dump_json(indent=2)
        json_size_kb = len(json_data.encode("utf-8")) / 1024

        # gzip圧縮
        compressed_data = gzip.compress(json_data.encode("utf-8"))
        compressed_size_kb = len(compressed_data) / 1024

        # ファイル名生成
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp_str}.backup.gz"
        output_path = output_dir / filename

        # ファイル保存
        output_path.write_bytes(compressed_data)

        logger.info(
            f"Total: {len(table_names) - 1} tables, {total_rows} rows"
        )  # -1 for alembic_version
        logger.info(
            f"Backup size: {json_size_kb:.2f} KB → {compressed_size_kb:.2f} KB (compressed)"
        )
        logger.info(f"Saved to: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise RuntimeError(f"Failed to create backup: {e}") from e


def calculate_diff(backup_path: Path) -> DiffSummary:
    """
    バックアップファイルと現在のデータベースの差分を計算する

    Args:
        backup_path: バックアップファイルのパス

    Returns:
        DiffSummary: 差分サマリ

    Raises:
        RuntimeError: 差分計算に失敗した場合
    """
    try:
        settings = get_settings()

        # バックアップファイルを読み込み
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        compressed_data = backup_path.read_bytes()
        json_data = gzip.decompress(compressed_data).decode("utf-8")
        backup_data = BackupData.model_validate_json(json_data)

        logger.info(f"Calculating diff with backup: {backup_path.name}")
        logger.info(f"Backup created at: {backup_data.metadata.timestamp.isoformat()}")

        # 現在のデータベースに接続
        engine = create_engine(settings.database_uri)
        inspector = inspect(engine)

        # テーブルごとの差分を計算
        table_diffs: dict[str, TableDiff] = {}
        total_current_rows = 0
        total_backup_rows = 0

        # バックアップに含まれるテーブル
        for table_name, table_backup in backup_data.tables.items():
            backup_rows = table_backup.row_count

            # 現在のテーブルの行数を取得
            if table_name in inspector.get_table_names():
                with engine.connect() as conn:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    ).fetchone()
                    current_rows = result[0] if result else 0
            else:
                # テーブルが存在しない場合
                current_rows = 0

            # 差分を計算
            diff = backup_rows - current_rows
            table_diffs[table_name] = TableDiff(
                current_rows=current_rows, backup_rows=backup_rows, diff=diff
            )

            total_current_rows += current_rows
            total_backup_rows += backup_rows

        # 現在のデータベースにのみ存在するテーブル
        current_table_names = set(inspector.get_table_names())
        backup_table_names = set(backup_data.tables.keys())
        only_in_current = current_table_names - backup_table_names - {"alembic_version"}

        for table_name in only_in_current:
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).fetchone()
                current_rows = result[0] if result else 0

            table_diffs[table_name] = TableDiff(
                current_rows=current_rows, backup_rows=0, diff=-current_rows
            )
            total_current_rows += current_rows

        # サマリ作成
        total_diff = total_backup_rows - total_current_rows
        diff_summary = DiffSummary(
            tables=table_diffs,
            total_current_rows=total_current_rows,
            total_backup_rows=total_backup_rows,
            total_diff=total_diff,
        )

        return diff_summary

    except Exception as e:
        logger.error(f"Failed to calculate diff: {e}")
        raise RuntimeError(f"Failed to calculate diff: {e}") from e
