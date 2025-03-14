#!/usr/bin/env python
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import boto3
import schedule
import sentry_sdk
from botocore.exceptions import ClientError
from pick import pick

# ロガー初期化
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("db-dumper")

# Sentry初期化
if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
        traces_sample_rate=1.0,
    )
    logger.info("Sentry initialized")

# S3設定
S3_ENDPOINT = os.environ.get("S3_ENDPOINT")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY")
S3_BUCKET = os.environ.get("S3_BUCKET", "test-bucket")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "default")

# ライフサイクル設定
BACKUP_RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
BACKUP_TIME = os.environ.get("BACKUP_TIME", "03:00")
BACKUP_HOUR = int(BACKUP_TIME.split(":")[0])
BACKUP_MINUTE = int(BACKUP_TIME.split(":")[1])

# データベース設定
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_NAME = os.environ.get("POSTGRES_DB", "main")
DB_USER = os.environ.get("POSTGRES_USER", "user")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")


def get_s3_client():
    """S3クライアントを取得（S3互換ストレージにも対応）"""
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


def ensure_backup_directory(s3_client):
    """バックアップディレクトリの存在確認と作成"""
    try:
        # ディレクトリの存在確認
        s3_client.head_object(Bucket=S3_BUCKET, Key=f"{BACKUP_DIR}/")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            # ディレクトリが存在しない場合、空のオブジェクトを作成してディレクトリとする
            try:
                s3_client.put_object(Bucket=S3_BUCKET, Key=f"{BACKUP_DIR}/")
                logger.info(f"Created backup directory: {BACKUP_DIR}/")
            except Exception as create_error:
                if "SENTRY_DSN" in os.environ:
                    sentry_sdk.capture_exception(create_error)
                logger.error(f"Error creating backup directory: {str(create_error)}")
                raise
        else:
            if "SENTRY_DSN" in os.environ:
                sentry_sdk.capture_exception(e)
            logger.error(f"Error checking backup directory: {str(e)}")
            raise


def list_backup_files(s3_client) -> List[str]:
    """バックアップファイルの一覧を取得"""
    backup_files = []
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=S3_BUCKET, Prefix=f"{BACKUP_DIR}/backup_"
        ):
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                filename = obj["Key"]
                if filename.startswith(f"{BACKUP_DIR}/backup_") and filename.endswith(
                    ".sql"
                ):
                    backup_files.append(filename)

        # 日付順に並び替え（新しい順）
        backup_files.sort(reverse=True)
    except Exception as e:
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        logger.error(f"Error listing backup files: {str(e)}")
        raise

    return backup_files


def list_old_backups(s3_client) -> List[str]:
    """指定した日数より古いバックアップを一覧取得"""
    cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
    old_backups = []

    try:
        # 指定されたディレクトリ内のオブジェクトを取得
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=S3_BUCKET, Prefix=f"{BACKUP_DIR}/backup_"
        ):
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                filename = ""
                try:
                    filename = obj["Key"]
                    # バックアップファイルのみを対象とする
                    if not filename.startswith(f"{BACKUP_DIR}/backup_"):
                        continue

                    date_str = filename.split("_")[1]
                    file_date = datetime.strptime(date_str, "%Y%m%d")

                    if file_date < cutoff_date:
                        old_backups.append(filename)
                except (IndexError, ValueError) as e:
                    if "SENTRY_DSN" in os.environ:
                        sentry_sdk.capture_exception(e)
                    logger.error(
                        f"Warning: Could not parse date from filename: {filename}"
                    )
                    continue

    except Exception as e:
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        logger.error(f"Error listing old backups: {str(e)}")

    return old_backups


def delete_old_backups(s3_client, old_backups: List[str]):
    """古いバックアップを削除"""
    if not old_backups:
        return

    try:
        objects_to_delete = [{"Key": key} for key in old_backups]
        s3_client.delete_objects(
            Bucket=S3_BUCKET, Delete={"Objects": objects_to_delete}
        )
        logger.info(f"Deleted {len(old_backups)} old backup(s) from {BACKUP_DIR}/")
    except Exception as e:
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        logger.error(f"Error deleting old backups: {str(e)}")


def select_backup_file() -> Optional[str]:
    """バックアップファイルを選択"""
    try:
        s3_client = get_s3_client()
        backup_files = list_backup_files(s3_client)

        if not backup_files:
            logger.error("No backup files found")
            return None

        # ファイル名から日時部分を抽出して表示用の文字列を作成
        display_options = []
        for filename in backup_files:
            try:
                # backup_YYYYMMDD_HHMMSS.sql の形式から日時を抽出
                date_str = filename.split("_")[1]
                time_str = filename.split("_")[2].split(".")[0]
                display_date = f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
                display_options.append(f"{display_date} - {filename}")
            except IndexError:
                display_options.append(filename)

        title = "Please select a backup file to restore (↑↓ to move, Enter to select):"
        selected_option, _ = pick(display_options, title)

        # 選択された表示用文字列からファイル名を抽出
        return selected_option.split(" - ")[-1]

    except Exception as e:
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        logger.error(f"Error selecting backup file: {str(e)}")
        return None


def create_backup():
    """バックアップを作成してS3にアップロード"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 安全な一時ディレクトリを使用
    backup_file = Path(tempfile.gettempdir()) / f"backup_{timestamp}.sql"
    backup_file_str = str(backup_file)

    try:
        # pg_dumpを実行
        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = DB_PASSWORD

            run = subprocess.run(
                [
                    "pg_dump",
                    f"--host={DB_HOST}",
                    f"--port={DB_PORT}",
                    f"--dbname={DB_NAME}",
                    f"--username={DB_USER}",
                    "--format=plain",
                    f"--file={backup_file_str}",
                ],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(
                run.stdout if run.stdout else "Database dump created successfully"
            )
        except subprocess.CalledProcessError as e:
            if "SENTRY_DSN" in os.environ:
                sentry_sdk.capture_exception(e)
            logger.error(f"Error running pg_dump: {e.stderr}")
            logger.error(f"pg_dump output: {e.stdout}")
            raise e

        # S3クライアントの初期化
        s3_client = get_s3_client()

        # バックアップディレクトリの確認/作成
        ensure_backup_directory(s3_client)

        # S3にアップロード
        s3_key = f"{BACKUP_DIR}/backup_{timestamp}.sql"
        s3_client.upload_file(backup_file_str, S3_BUCKET, s3_key)

        logger.info(f"Backup completed successfully: {s3_key}")

        # 古いバックアップの削除
        old_backups = list_old_backups(s3_client)
        if old_backups:
            delete_old_backups(s3_client, old_backups)

        # 一時ファイルを削除
        os.remove(backup_file_str)

        # filenameを返す
        return s3_key

    except Exception as e:
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        logger.error(f"Backup failed: {str(e)}")


def restore_backup(backup_file: str):
    """バックアップをリストア"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 安全な一時ディレクトリを使用
    local_file = Path(tempfile.gettempdir()) / f"restore_{timestamp}.sql"
    local_file_str = str(local_file)

    try:
        # S3からファイルをダウンロード
        s3_client = get_s3_client()
        logger.info(f"Downloading backup file: {backup_file}")
        s3_client.download_file(S3_BUCKET, backup_file, local_file_str)

        # データベースに接続してリストアを実行
        logger.info("Starting database restore...")
        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = DB_PASSWORD

            # まず既存の接続を切断
            disconnect_cmd = f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{DB_NAME}' AND pid <> pg_backend_pid();"
            subprocess.run(
                [
                    "psql",
                    f"--host={DB_HOST}",
                    f"--port={DB_PORT}",
                    f"--dbname={DB_NAME}",
                    f"--username={DB_USER}",
                    "-c",
                    disconnect_cmd,
                ],
                env=env,
                check=True,
                capture_output=True,
            )

            # データベースを再作成
            subprocess.run(
                [
                    "psql",
                    f"--host={DB_HOST}",
                    f"--port={DB_PORT}",
                    "--dbname=postgres",
                    f"--username={DB_USER}",
                    "-c",
                    f"DROP DATABASE IF EXISTS {DB_NAME};",
                ],
                env=env,
                check=True,
                capture_output=True,
            )

            subprocess.run(
                [
                    "psql",
                    f"--host={DB_HOST}",
                    f"--port={DB_PORT}",
                    "--dbname=postgres",
                    f"--username={DB_USER}",
                    "-c",
                    f"CREATE DATABASE {DB_NAME};",
                ],
                env=env,
                check=True,
                capture_output=True,
            )

            # バックアップを復元
            subprocess.run(
                [
                    "psql",
                    f"--host={DB_HOST}",
                    f"--port={DB_PORT}",
                    f"--dbname={DB_NAME}",
                    f"--username={DB_USER}",
                    "-f",
                    local_file_str,
                ],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info("Database restore completed successfully")

        except subprocess.CalledProcessError as e:
            if "SENTRY_DSN" in os.environ:
                sentry_sdk.capture_exception(e)
            logger.error(f"Error during database restore: {e.stderr}")
            raise

    except Exception as e:
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        logger.error(f"Restore failed: {str(e)}")
        raise
    finally:
        # 一時ファイルを削除
        if os.path.exists(local_file_str):
            os.remove(local_file_str)


def perform_backup():
    """バックアップを実行して古いファイルをクリーンアップ"""
    create_backup()


def list_backups():
    """最近のバックアップを表示"""
    if not all([S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET]):
        print("Storage credentials or bucket not configured, cannot list backups")
        return

    s3_client = get_s3_client()
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=f"{BACKUP_DIR}/")

        if "Contents" in response:
            print("\nRecent backups:")
            for obj in sorted(
                response["Contents"], key=lambda x: x["LastModified"], reverse=True
            )[:10]:
                size_mb = obj["Size"] / (1024 * 1024)
                print(f"{obj['Key']} - {obj['LastModified']} - {size_mb:.2f} MB")
            print()
        else:
            print("No backups found\n")
    except Exception as e:
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        print(f"Error listing backups: {str(e)}")


def run_scheduled_backups():
    """スケジュールに従ってバックアップを実行"""
    logger.info(f"Starting backup service for directory: {BACKUP_DIR}/")
    logger.info(f"Retention period: {BACKUP_RETENTION_DAYS} days")
    logger.info(f"Scheduled backup time: {BACKUP_HOUR:02d}:{BACKUP_MINUTE:02d}")

    # 指定された時刻にバックアップを実行
    schedule.every().day.at(f"{BACKUP_HOUR:02d}:{BACKUP_MINUTE:02d}").do(perform_backup)

    # スケジュールを監視し続ける
    while True:
        schedule.run_pending()
        time.sleep(60)


def run_interactive_mode():
    """対話モードでバックアップ操作を実行"""
    title = "DB Dumper - Choose an operation"
    options = ["Create backup now", "List recent backups", "Restore backup", "Exit"]

    while True:
        option, _ = pick(options, title)

        if option == "Create backup now":
            perform_backup()
        elif option == "List recent backups":
            list_backups()
        elif option == "Restore backup":
            backup_file = select_backup_file()
            if backup_file:
                confirm_title = (
                    f"Restore {backup_file}? This will OVERWRITE the current database!"
                )
                confirm_options = ["Yes, proceed with restore", "No, cancel"]
                confirm, _ = pick(confirm_options, confirm_title)
                if confirm.startswith("Yes"):
                    restore_backup(backup_file)
            else:
                print("No backup file selected or no backups found")
        else:
            break


def main():
    """メイン関数"""
    # 第1引数取得
    arg1 = sys.argv[1] if len(sys.argv) > 1 else None
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None

    if arg1 == "oneshot":
        logger.info("Running oneshot backup")
        create_backup()
    elif arg1 == "restore":
        logger.info("Starting restore process")
        if arg2:
            restore_backup(arg2)
        else:
            backup_file = select_backup_file()
            if backup_file:
                restore_backup(backup_file)
            else:
                logger.error("No backup file selected")
    elif arg1 == "list":
        list_backups()
    elif arg1 == "test" and arg2 == "--confirm":
        logger.info("Running test backup")
        filename = create_backup()
        # リストアを試行
        if filename:
            restore_backup(filename)
            # 削除
            s3_client = get_s3_client()
            s3_client.delete_object(Bucket=S3_BUCKET, Key=filename)
            # 作成したディレクトリも削除
            s3_client.delete_object(Bucket=S3_BUCKET, Key=f"{BACKUP_DIR}/")
        logger.info("Test completed")
    else:
        # 環境変数からモードを決定
        mode = os.environ.get("DUMPER_MODE", "scheduled")

        if mode == "interactive":
            run_interactive_mode()
        elif mode == "stop":
            pass
        else:
            run_scheduled_backups()


if __name__ == "__main__":
    main()
