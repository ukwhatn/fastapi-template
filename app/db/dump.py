#!/usr/bin/env python
import os
import time
import datetime
import subprocess
import schedule
import logging
import boto3
from botocore.exceptions import ClientError
import sentry_sdk
from pick import pick

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("db-dumper")

# Configure Sentry if SENTRY_DSN is provided
if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
        traces_sample_rate=1.0,
    )
    logger.info("Sentry initialized")

# Database connection parameters from environment variables
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "main")
DB_USER = os.environ.get("POSTGRES_USER", "user")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")

# AWS S3 configuration
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
S3_BUCKET = os.environ.get("S3_BUCKET")
S3_PREFIX = os.environ.get("S3_PREFIX", "db-backups")

# Backup schedule (default: daily at 03:00)
BACKUP_HOUR = int(os.environ.get("BACKUP_HOUR", "3"))
BACKUP_MINUTE = int(os.environ.get("BACKUP_MINUTE", "0"))

# Retention settings (default: keep 7 days of backups)
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "7"))


def create_db_dump(output_file):
    """Create a PostgreSQL database dump"""
    cmd = [
        "pg_dump",
        f"--host={DB_HOST}",
        f"--port={DB_PORT}",
        f"--username={DB_USER}",
        f"--dbname={DB_NAME}",
        "--format=custom",
        f"--file={output_file}",
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    try:
        logger.info(f"Creating database dump: {output_file}")
        subprocess.run(cmd, env=env, check=True, capture_output=True)
        logger.info("Database dump created successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create database dump: {e}")
        logger.error(f"stdout: {e.stdout.decode()}")
        logger.error(f"stderr: {e.stderr.decode()}")
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        return False


def upload_to_s3(file_path, s3_key):
    """Upload file to S3"""
    if not all([AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET]):
        logger.warning(
            "AWS credentials or S3 bucket not configured, skipping S3 upload"
        )
        return True

    try:
        logger.info(f"Uploading {file_path} to S3 bucket {S3_BUCKET}/{s3_key}")
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION,
        )
        s3.upload_file(file_path, S3_BUCKET, s3_key)
        logger.info("Upload to S3 completed successfully")
        return True
    except ClientError as e:
        logger.error(f"Failed to upload to S3: {e}")
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)
        return False


def cleanup_old_backups():
    """Clean up backups older than RETENTION_DAYS"""
    if not all([AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET]):
        logger.warning("AWS credentials or S3 bucket not configured, skipping cleanup")
        return

    try:
        logger.info(f"Cleaning up backups older than {RETENTION_DAYS} days")
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION,
        )

        # Calculate cutoff date
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=RETENTION_DAYS)
        cutoff_timestamp = cutoff_date.timestamp()

        # List objects in the bucket with the prefix
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX):
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                if obj["LastModified"].timestamp() < cutoff_timestamp:
                    logger.info(f"Deleting old backup: {obj['Key']}")
                    s3.delete_object(Bucket=S3_BUCKET, Key=obj["Key"])

        logger.info("Cleanup completed")
    except ClientError as e:
        logger.error(f"Failed to cleanup old backups: {e}")
        if "SENTRY_DSN" in os.environ:
            sentry_sdk.capture_exception(e)


def perform_backup():
    """Perform a full database backup"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_filename = f"{DB_NAME}_{timestamp}.dump"
    local_path = f"/tmp/{dump_filename}"

    # Create the database dump
    if not create_db_dump(local_path):
        return

    # Upload to S3
    s3_key = f"{S3_PREFIX}/{dump_filename}"
    if upload_to_s3(local_path, s3_key):
        # Clean up local file
        os.remove(local_path)
        logger.info(f"Local file {local_path} removed")

    # Clean up old backups
    cleanup_old_backups()


def run_scheduled_backups():
    """Run scheduled backups"""
    logger.info(f"Scheduling daily backup at {BACKUP_HOUR:02d}:{BACKUP_MINUTE:02d}")
    schedule.every().day.at(f"{BACKUP_HOUR:02d}:{BACKUP_MINUTE:02d}").do(perform_backup)

    # Run an immediate backup
    logger.info("Running immediate backup")
    perform_backup()

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)


def run_interactive_mode():
    """Run in interactive mode for manual backup operations"""
    title = "DB Dumper - Choose an operation"
    options = ["Create backup now", "List recent backups", "Exit"]

    while True:
        option, _ = pick(options, title)

        if option == "Create backup now":
            perform_backup()
        elif option == "List recent backups":
            if not all([AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_BUCKET]):
                print(
                    "AWS credentials or S3 bucket not configured, cannot list backups"
                )
                continue

            s3 = boto3.client(
                "s3",
                aws_access_key_id=AWS_ACCESS_KEY,
                aws_secret_access_key=AWS_SECRET_KEY,
                region_name=AWS_REGION,
            )

            response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)

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
        else:
            break


if __name__ == "__main__":
    # Determine the mode based on environment variables
    mode = os.environ.get("DUMPER_MODE", "scheduled")

    if mode == "interactive":
        run_interactive_mode()
    else:
        run_scheduled_backups()
