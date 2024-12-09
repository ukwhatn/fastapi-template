import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional

import boto3
import schedule
import sentry_sdk
from botocore.exceptions import ClientError
from pick import pick

# S3設定
S3_ENDPOINT = os.environ['S3_ENDPOINT']
S3_ACCESS_KEY = os.environ['S3_ACCESS_KEY']
S3_SECRET_KEY = os.environ['S3_SECRET_KEY']
S3_BUCKET = os.environ['S3_BUCKET']
BACKUP_DIR = os.environ.get('BACKUP_DIR', 'default')

# ライフサイクル設定
BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
BACKUP_TIME = os.environ.get('BACKUP_TIME', '03:00')

# データベース設定
DB_HOST = os.environ['POSTGRES_HOST']
DB_NAME = os.environ['POSTGRES_DB']
DB_USER = os.environ['POSTGRES_USER']
DB_PASSWORD = os.environ['POSTGRES_PASSWORD']

# ロガー
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Sentry
SENTRY_DSN = os.environ.get('SENTRY_DSN', None)
if SENTRY_DSN is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0
    )


def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY
    )


def ensure_backup_directory(s3_client):
    """バックアップディレクトリの存在確認と作成"""
    try:
        # ディレクトリの存在確認
        s3_client.head_object(Bucket=S3_BUCKET, Key=f'{BACKUP_DIR}/')
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # ディレクトリが存在しない場合、空のオブジェクトを作成してディレクトリとする
            try:
                s3_client.put_object(Bucket=S3_BUCKET, Key=f'{BACKUP_DIR}/')
                LOGGER.info(f"Created backup directory: {BACKUP_DIR}/")
            except Exception as create_error:
                sentry_sdk.capture_exception(create_error)
                LOGGER.error(f"Error creating backup directory: {str(create_error)}")
                raise
        else:
            sentry_sdk.capture_exception(e)
            LOGGER.error(f"Error checking backup directory: {str(e)}")
            raise


def list_backup_files(s3_client) -> List[str]:
    """バックアップファイルの一覧を取得"""
    backup_files = []
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=f'{BACKUP_DIR}/backup_'):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                filename = obj['Key']
                if filename.startswith(f'{BACKUP_DIR}/backup_') and filename.endswith('.sql'):
                    backup_files.append(filename)

        # 日付順に並び替え（新しい順）
        backup_files.sort(reverse=True)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        LOGGER.error(f"Error listing backup files: {str(e)}")
        raise

    return backup_files


def list_old_backups(s3_client) -> List[str]:
    """指定した日数より古いバックアップを一覧取得"""
    cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
    old_backups = []

    try:
        # 指定されたディレクトリ内のオブジェクトを取得
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=f'{BACKUP_DIR}/backup_'):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                filename = ''
                try:
                    filename = obj['Key']
                    # バックアップファイルのみを対象とする
                    if not filename.startswith(f'{BACKUP_DIR}/backup_'):
                        continue

                    date_str = filename.split('_')[1]
                    file_date = datetime.strptime(date_str, '%Y%m%d')

                    if file_date < cutoff_date:
                        old_backups.append(filename)
                except (IndexError, ValueError) as e:
                    sentry_sdk.capture_exception(e)
                    LOGGER.error(f"Warning: Could not parse date from filename: {filename}")
                    continue

    except Exception as e:
        sentry_sdk.capture_exception(e)
        LOGGER.error(f"Error listing old backups: {str(e)}")

    return old_backups


def delete_old_backups(s3_client, old_backups: List[str]):
    """古いバックアップを削除"""
    if not old_backups:
        return

    try:
        objects_to_delete = [{'Key': key} for key in old_backups]
        s3_client.delete_objects(
            Bucket=S3_BUCKET,
            Delete={'Objects': objects_to_delete}
        )
        LOGGER.info(f"Deleted {len(old_backups)} old backup(s) from {BACKUP_DIR}/")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        LOGGER.error(f"Error deleting old backups: {str(e)}")


def select_backup_file() -> Optional[str]:
    """バックアップファイルを選択"""
    try:
        s3_client = get_s3_client()
        backup_files = list_backup_files(s3_client)

        if not backup_files:
            LOGGER.error("No backup files found")
            return None

        # ファイル名から日時部分を抽出して表示用の文字列を作成
        display_options = []
        for filename in backup_files:
            try:
                # backup_YYYYMMDD_HHMMSS.sql の形式から日時を抽出
                date_str = filename.split('_')[1]
                time_str = filename.split('_')[2].split('.')[0]
                display_date = f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
                display_options.append(f"{display_date} - {filename}")
            except IndexError:
                display_options.append(filename)

        title = 'Please select a backup file to restore (↑↓ to move, Enter to select):'
        selected_option, _ = pick(display_options, title)

        # 選択された表示用文字列からファイル名を抽出
        return selected_option.split(' - ')[-1]

    except Exception as e:
        sentry_sdk.capture_exception(e)
        LOGGER.error(f"Error selecting backup file: {str(e)}")
        return None


def create_backup():
    """バックアップを作成してS3にアップロード"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'/tmp/backup_{timestamp}.sql'

    try:
        # pg_dumpを実行
        try:
            run = subprocess.run([
                'pg_dump',
                f'--host={DB_HOST}',
                f'--dbname={DB_NAME}',
                f'--username={DB_USER}',
                '--format=plain',
                f'--file={backup_file}'
            ], env={'PGPASSWORD': DB_PASSWORD}, check=True, capture_output=True, text=True)
            LOGGER.info(run.stdout)
        except subprocess.CalledProcessError as e:
            sentry_sdk.capture_exception(e)
            LOGGER.error(f'Error running pg_dump: {e.stderr}')
            LOGGER.error(f'pg_dump output: {e.stdout}')
            raise e

        # S3クライアントの初期化
        s3_client = get_s3_client()

        # バックアップディレクトリの確認/作成
        ensure_backup_directory(s3_client)

        # S3にアップロード
        s3_key = f'{BACKUP_DIR}/backup_{timestamp}.sql'
        s3_client.upload_file(
            backup_file,
            S3_BUCKET,
            s3_key
        )

        LOGGER.info(f'Backup completed successfully: {s3_key}')

        # 古いバックアップの削除
        old_backups = list_old_backups(s3_client)
        if old_backups:
            delete_old_backups(s3_client, old_backups)

        # 一時ファイルを削除
        os.remove(backup_file)

    except Exception as e:
        sentry_sdk.capture_exception(e)
        LOGGER.error(f'Backup failed: {str(e)}')


def restore_backup(backup_file: str):
    """バックアップをリストア"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    local_file = f'/tmp/restore_{timestamp}.sql'

    try:
        # S3からファイルをダウンロード
        s3_client = get_s3_client()
        LOGGER.info(f"Downloading backup file: {backup_file}")
        s3_client.download_file(S3_BUCKET, backup_file, local_file)

        # データベースに接続してリストアを実行
        LOGGER.info("Starting database restore...")
        try:
            # まず既存の接続を切断
            disconnect_cmd = f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{DB_NAME}' AND pid <> pg_backend_pid();"
            subprocess.run([
                'psql',
                f'--host={DB_HOST}',
                f'--dbname={DB_NAME}',
                f'--username={DB_USER}',
                '-c', disconnect_cmd
            ], env={'PGPASSWORD': DB_PASSWORD}, check=True, capture_output=True)

            # データベースを再作成
            subprocess.run([
                'psql',
                f'--host={DB_HOST}',
                '--dbname=postgres',
                f'--username={DB_USER}',
                '-c', f'DROP DATABASE IF EXISTS {DB_NAME};'
            ], env={'PGPASSWORD': DB_PASSWORD}, check=True, capture_output=True)

            subprocess.run([
                'psql',
                f'--host={DB_HOST}',
                '--dbname=postgres',
                f'--username={DB_USER}',
                '-c', f'CREATE DATABASE {DB_NAME};'
            ], env={'PGPASSWORD': DB_PASSWORD}, check=True, capture_output=True)

            # バックアップを復元
            restore_result = subprocess.run([
                'psql',
                f'--host={DB_HOST}',
                f'--dbname={DB_NAME}',
                f'--username={DB_USER}',
                '-f', local_file
            ], env={'PGPASSWORD': DB_PASSWORD}, check=True, capture_output=True, text=True)

            LOGGER.info("Database restore completed successfully")

        except subprocess.CalledProcessError as e:
            sentry_sdk.capture_exception(e)
            LOGGER.error(f"Error during database restore: {e.stderr}")
            raise

    except Exception as e:
        sentry_sdk.capture_exception(e)
        LOGGER.error(f"Restore failed: {str(e)}")
        raise
    finally:
        # 一時ファイルを削除
        if os.path.exists(local_file):
            os.remove(local_file)


def main():
    LOGGER.info(f"Starting backup/restore service for directory: {BACKUP_DIR}/")

    # 第1引数取得
    arg1 = sys.argv[1] if len(sys.argv) > 1 else None

    if arg1 == "oneshot":
        LOGGER.info("Running oneshot backup")
        create_backup()
    elif arg1 == "restore":
        LOGGER.info("Starting restore process")
        backup_file = select_backup_file()
        if backup_file:
            restore_backup(backup_file)
        else:
            LOGGER.error("No backup file selected")
    else:
        LOGGER.info(f"Retention period: {BACKUP_RETENTION_DAYS} days")
        LOGGER.info(f"Scheduled backup time: {BACKUP_TIME}")

        # 指定された時刻にバックアップを実行
        schedule.every().day.at(BACKUP_TIME).do(create_backup)

        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    main()
