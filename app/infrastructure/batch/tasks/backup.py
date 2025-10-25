"""データベースバックアップタスク"""

import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import opendal

from app.core.config import get_settings
from app.infrastructure.batch.base import BatchTask
from app.infrastructure.batch.registry import task_registry


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

        1. pg_dumpでダンプファイルを作成
        2. ローカルディレクトリに保存
        3. S3にアップロード（設定がある場合）
        4. 古いバックアップを削除
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.dump"

        with tempfile.TemporaryDirectory() as tmpdir:
            dump_path = Path(tmpdir) / filename

            # pg_dumpでダンプ作成
            self._create_dump(dump_path)

            # ローカルに保存
            self._save_local(dump_path, filename)

            # S3にアップロード
            if self.storage:
                self._upload_to_s3(dump_path, filename)

        # 古いバックアップを削除
        self._cleanup_old_backups()

    def _create_dump(self, output_path: Path) -> None:
        """
        pg_dumpでダンプファイルを作成する。

        Args:
            output_path: ダンプファイルの出力先パス

        Raises:
            subprocess.CalledProcessError: pg_dump実行に失敗した場合
        """
        cmd = [
            "pg_dump",
            "-h",
            self.settings.POSTGRES_HOST,
            "-p",
            str(self.settings.POSTGRES_PORT),
            "-U",
            self.settings.POSTGRES_USER,
            "-d",
            self.settings.POSTGRES_DB,
            "-F",
            "c",  # カスタムフォーマット（圧縮済み）
            "-f",
            str(output_path),
        ]

        env = {"PGPASSWORD": self.settings.POSTGRES_PASSWORD}

        self.logger.info(f"Creating database dump: {output_path.name}")
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        self.logger.info(
            f"Dump created: {output_path} ({output_path.stat().st_size} bytes)"
        )

    def _save_local(self, source_path: Path, filename: str) -> None:
        """
        ダンプファイルをローカルディレクトリに保存する。

        Args:
            source_path: コピー元のファイルパス
            filename: 保存するファイル名
        """
        local_backup_dir = Path("./backups")
        local_backup_dir.mkdir(exist_ok=True)

        dest_path = local_backup_dir / filename
        shutil.copy(source_path, dest_path)
        self.logger.info(f"Saved to local: {dest_path}")

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
            for backup_file in local_backup_dir.glob("backup_*.dump"):
                # ファイル名から日時を抽出
                try:
                    timestamp_str = backup_file.stem.replace("backup_", "")
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
            # Note: OpenDALのlistやdeleteの実装は省略
            # 必要に応じて後で実装
            pass


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
