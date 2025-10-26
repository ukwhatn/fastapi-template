"""データベースバックアップタスク"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import opendal

from app.core.config import get_settings
from app.infrastructure.batch.base import BatchTask
from app.infrastructure.batch.registry import task_registry
from app.infrastructure.database.backup.core import create_backup


class BackupTask(BatchTask):
    """
    データベースバックアップタスク。

    pg_dumpを使用してPostgreSQLデータベースをバックアップし、
    ローカルディスクとS3互換ストレージに保存する。
    """

    def __init__(self) -> None:
        """バックアップタスクを初期化する。"""
        super().__init__()
        self.settings = get_settings()
        self.storage: Optional[opendal.Operator] = None
        self._init_storage()

    def _init_storage(self) -> None:
        """
        S3ストレージを初期化する。

        S3設定が環境変数に存在する場合のみ初期化する。
        設定がない場合はローカルのみに保存される。
        """
        if (
            self.settings.S3_ENDPOINT
            and self.settings.S3_BUCKET
            and self.settings.S3_ACCESS_KEY
        ):
            try:
                self.storage = opendal.Operator(
                    "s3",
                    endpoint=self.settings.S3_ENDPOINT,
                    bucket=self.settings.S3_BUCKET,
                    access_key_id=self.settings.S3_ACCESS_KEY,
                    secret_access_key=self.settings.S3_SECRET_KEY,
                    region=self.settings.S3_REGION or "auto",
                )
                self.logger.info("S3 storage initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize S3 storage: {e}")
                self.storage = None
        else:
            self.logger.info("S3 storage not configured, using local storage only")

    def execute(self) -> None:
        """
        バックアップを実行する。

        1. psycopg2でバックアップファイルを作成
        2. S3にアップロード（設定がある場合）
        3. 古いバックアップを削除
        """
        # バックアップを作成（ローカルディレクトリに保存される）
        backup_path = create_backup()

        # S3にアップロード
        if self.storage:
            self._upload_to_s3(backup_path, backup_path.name)

        # 古いバックアップを削除
        self._cleanup_old_backups()

    def _upload_to_s3(self, file_path: Path, remote_name: str) -> None:
        """
        ダンプファイルをS3にアップロードする。

        Args:
            file_path: アップロードするファイルパス
            remote_name: S3上のファイル名

        Raises:
            Exception: アップロードに失敗した場合
        """
        if not self.storage:
            return

        try:
            with open(file_path, "rb") as f:
                self.storage.write(remote_name, f.read())
            self.logger.info(f"Uploaded to S3: {remote_name}")
        except Exception as e:
            self.logger.error(f"Failed to upload to S3: {e}")
            raise

    def _cleanup_old_backups(self) -> None:
        """
        保持期限を過ぎたバックアップファイルを削除する。

        BACKUP_RETENTION_DAYSで指定された日数より古いファイルを削除する。
        """
        retention_days = self.settings.BACKUP_RETENTION_DAYS or 7
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # ローカルファイルのクリーンアップ
        local_backup_dir = Path("./backups")
        if local_backup_dir.exists():
            for backup_file in local_backup_dir.glob("backup_*.backup.gz"):
                # ファイル名から日時を抽出
                try:
                    # backup_20250101_120000.backup.gz -> 20250101_120000
                    timestamp_str = backup_file.stem.replace(".backup", "").replace(
                        "backup_", ""
                    )
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                    if file_date < cutoff_date:
                        backup_file.unlink()
                        self.logger.info(
                            f"Deleted old local backup: {backup_file.name}"
                        )
                except (ValueError, OSError) as e:
                    self.logger.warning(f"Failed to process {backup_file.name}: {e}")

        # S3ファイルのクリーンアップ
        if self.storage:
            try:
                # S3上のバックアップファイルをリスト
                entries = self.storage.list("")
                for entry in entries:
                    if not entry.path.startswith("backup_"):
                        continue
                    if not entry.path.endswith(".backup.gz"):
                        continue

                    # ファイル名からタイムスタンプを抽出
                    try:
                        # backup_20250101_120000.backup.gz -> 20250101_120000
                        timestamp_str = entry.path.replace("backup_", "").replace(
                            ".backup.gz", ""
                        )
                        file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                        if file_date < cutoff_date:
                            self.storage.delete(entry.path)
                            self.logger.info(f"Deleted old S3 backup: {entry.path}")
                    except (ValueError, Exception) as e:
                        self.logger.warning(
                            f"Failed to process S3 file {entry.path}: {e}"
                        )
            except Exception as e:
                self.logger.error(f"Failed to cleanup S3 backups: {e}")


def run_backup() -> None:
    """
    バックアップタスクを実行する。

    スケジューラーおよびCLIから呼び出される。
    """
    BackupTask().run()


# タスクをレジストリに登録
backup_schedule = get_settings().BACKUP_SCHEDULE
if backup_schedule:
    task_registry.register(
        task_id="database_backup",
        func=run_backup,
        cron=backup_schedule,
        description="Database backup task",
    )
