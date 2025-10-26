"""バックアップ管理CLI"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click
import opendal

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_local_backups() -> List[Path]:
    """
    ローカルバックアップファイルのリストを取得する。

    Returns:
        バックアップファイルのパスリスト（日付降順）
    """
    local_backup_dir = Path("./backups")
    if not local_backup_dir.exists():
        return []

    backups = sorted(
        local_backup_dir.glob("backup_*.backup.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return backups


def get_s3_backups() -> List[str]:
    """
    S3バックアップファイルのリストを取得する。

    Returns:
        S3上のバックアップファイル名リスト
    """
    settings = get_settings()

    if not (settings.S3_ENDPOINT and settings.S3_BUCKET and settings.S3_ACCESS_KEY):
        return []

    try:
        storage = opendal.Operator(
            "s3",
            endpoint=settings.S3_ENDPOINT,
            bucket=settings.S3_BUCKET,
            access_key_id=settings.S3_ACCESS_KEY,
            secret_access_key=settings.S3_SECRET_KEY,
            region=settings.S3_REGION or "us-east-1",
        )

        # OpenDALのlist機能を使用してバックアップファイルを列挙
        entries = storage.list("")
        backups = [
            entry.path
            for entry in entries
            if entry.path.startswith("backup_") and entry.path.endswith(".backup.gz")
        ]
        return sorted(backups, reverse=True)
    except Exception as e:
        logger.error(f"Failed to list S3 backups: {e}")
        return []


@click.group()
def cli() -> None:
    """データベースバックアップ管理CLI"""
    pass


@cli.command("oneshot")
def backup_oneshot() -> None:
    """バックアップを即座に実行する"""
    from app.infrastructure.batch.tasks.backup import run_backup

    click.echo("Starting manual backup...")
    try:
        run_backup()
        click.echo("✓ Backup completed successfully")
    except Exception as e:
        click.echo(f"✗ Backup failed: {e}", err=True)
        raise click.Abort()


@cli.command("list")
@click.option(
    "--remote",
    is_flag=True,
    help="S3上のバックアップも表示",
)
def backup_list(remote: bool) -> None:
    """利用可能なバックアップファイルを一覧表示する"""
    # ローカルバックアップ
    local_backups = get_local_backups()

    if local_backups:
        click.echo("Local backups:")
        for backup in local_backups:
            size_mb = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            click.echo(f"  - {backup.name} ({size_mb:.2f} MB, {mtime})")
    else:
        click.echo("No local backups found")

    # S3バックアップ
    if remote:
        s3_backups = get_s3_backups()
        if s3_backups:
            click.echo("\nS3 backups:")
            for s3_backup in s3_backups:
                click.echo(f"  - {s3_backup}")
        else:
            click.echo("\nNo S3 backups found (or S3 not configured)")


@cli.command("diff")
@click.argument("backup_file")
@click.option(
    "--from-s3",
    is_flag=True,
    help="S3からバックアップを取得",
)
def backup_diff(backup_file: str, from_s3: bool) -> None:
    """
    バックアップと現在のデータベースの差分を表示する。

    BACKUP_FILE: 比較するバックアップファイル名
    """
    from app.infrastructure.database.backup.core import calculate_diff

    settings = get_settings()

    restore_path: Optional[Path] = None

    try:
        # S3からダウンロード
        if from_s3:
            if not (
                settings.S3_ENDPOINT and settings.S3_BUCKET and settings.S3_ACCESS_KEY
            ):
                click.echo("✗ S3 storage not configured", err=True)
                raise click.Abort()

            click.echo(f"Downloading from S3: {backup_file}")

            storage = opendal.Operator(
                "s3",
                endpoint=settings.S3_ENDPOINT,
                bucket=settings.S3_BUCKET,
                access_key_id=settings.S3_ACCESS_KEY,
                secret_access_key=settings.S3_SECRET_KEY,
                region=settings.S3_REGION or "us-east-1",
            )

            data = storage.read(backup_file)

            # 一時ファイルに保存
            import tempfile

            temp_dir = Path(tempfile.mkdtemp())
            restore_path = temp_dir / backup_file
            restore_path.write_bytes(data)
        else:
            # ローカルファイル
            restore_path = Path("./backups") / backup_file
            if not restore_path.exists():
                click.echo(f"✗ Backup file not found: {restore_path}", err=True)
                raise click.Abort()

        # Diffを計算
        click.echo(f"Calculating diff for: {backup_file}")
        diff_summary = calculate_diff(restore_path)

        click.echo("\nBackup diff summary:")
        for table_name, table_diff in diff_summary.tables.items():
            sign = "+" if table_diff.diff > 0 else ""
            click.echo(
                f"  {table_name}: {table_diff.current_rows} rows → {table_diff.backup_rows} rows ({sign}{table_diff.diff})"
            )

        sign = "+" if diff_summary.total_diff > 0 else ""
        click.echo(
            f"\nTotal: {diff_summary.total_current_rows} rows → {diff_summary.total_backup_rows} rows ({sign}{diff_summary.total_diff})"
        )

    except Exception as e:
        click.echo(f"✗ Failed to calculate diff: {e}", err=True)
        raise click.Abort()
    finally:
        # S3からダウンロードした場合、一時ファイルを削除
        if from_s3 and restore_path and restore_path.parent.name.startswith("tmp"):
            import shutil

            shutil.rmtree(restore_path.parent, ignore_errors=True)


@cli.command("restore")
@click.argument("backup_file")
@click.option(
    "--from-s3",
    is_flag=True,
    help="S3からバックアップを取得",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="確認をスキップ",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="差分のみ表示（リストアは実行しない）",
)
def backup_restore(backup_file: str, from_s3: bool, yes: bool, dry_run: bool) -> None:
    """
    バックアップからデータベースをリストアする。

    BACKUP_FILE: リストアするバックアップファイル名
    """
    from app.infrastructure.database.backup.core import calculate_diff, restore_backup

    settings = get_settings()

    restore_path: Optional[Path] = None

    try:
        # S3からダウンロード
        if from_s3:
            if not (
                settings.S3_ENDPOINT and settings.S3_BUCKET and settings.S3_ACCESS_KEY
            ):
                click.echo("✗ S3 storage not configured", err=True)
                raise click.Abort()

            click.echo(f"Downloading from S3: {backup_file}")

            storage = opendal.Operator(
                "s3",
                endpoint=settings.S3_ENDPOINT,
                bucket=settings.S3_BUCKET,
                access_key_id=settings.S3_ACCESS_KEY,
                secret_access_key=settings.S3_SECRET_KEY,
                region=settings.S3_REGION or "us-east-1",
            )

            data = storage.read(backup_file)

            # 一時ファイルに保存
            import tempfile

            temp_dir = Path(tempfile.mkdtemp())
            restore_path = temp_dir / backup_file
            restore_path.write_bytes(data)
            click.echo(f"Downloaded to: {restore_path}")
        else:
            # ローカルファイル
            restore_path = Path("./backups") / backup_file
            if not restore_path.exists():
                click.echo(f"✗ Backup file not found: {restore_path}", err=True)
                raise click.Abort()

        # Dry-runモード（差分のみ表示）
        if dry_run:
            click.echo(f"Dry-run mode: Calculating diff for {backup_file}")
            diff_summary = calculate_diff(restore_path)

            click.echo("\nBackup diff summary:")
            for table_name, table_diff in diff_summary.tables.items():
                sign = "+" if table_diff.diff > 0 else ""
                click.echo(
                    f"  {table_name}: {table_diff.current_rows} rows → {table_diff.backup_rows} rows ({sign}{table_diff.diff})"
                )

            sign = "+" if diff_summary.total_diff > 0 else ""
            click.echo(
                f"\nTotal: {diff_summary.total_current_rows} rows → {diff_summary.total_backup_rows} rows ({sign}{diff_summary.total_diff})"
            )
            click.echo("\n(No changes made - dry-run mode)")
            return

        # 確認プロンプト（diffを表示）
        if not yes:
            click.echo(f"Calculating diff for {backup_file}...")
            diff_summary = calculate_diff(restore_path)

            click.echo("\nBackup diff summary:")
            for table_name, table_diff in diff_summary.tables.items():
                sign = "+" if table_diff.diff > 0 else ""
                click.echo(
                    f"  {table_name}: {table_diff.current_rows} rows → {table_diff.backup_rows} rows ({sign}{table_diff.diff})"
                )

            sign = "+" if diff_summary.total_diff > 0 else ""
            click.echo(
                f"\nTotal: {diff_summary.total_current_rows} rows → {diff_summary.total_backup_rows} rows ({sign}{diff_summary.total_diff})"
            )

            click.confirm(
                f"\n⚠️  Database '{settings.POSTGRES_DB}' will be restored from '{backup_file}'. "
                "All current data will be lost. Continue?",
                abort=True,
            )

        # リストア実行
        click.echo(f"Restoring database from: {restore_path}")
        result = restore_backup(restore_path, show_diff=False)  # diffは既に表示済み

        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"✗ {result.message}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"✗ Restore failed: {e}", err=True)
        raise click.Abort()
    finally:
        # S3からダウンロードした場合、一時ファイルを削除
        if from_s3 and restore_path and restore_path.parent.name.startswith("tmp"):
            import shutil

            shutil.rmtree(restore_path.parent, ignore_errors=True)


if __name__ == "__main__":
    cli()
