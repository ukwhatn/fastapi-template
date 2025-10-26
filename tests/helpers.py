"""PostgreSQLテスト用ヘルパー関数"""

import uuid
from typing import Any

import psycopg2
from alembic import command
from alembic.config import Config
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.core.config import get_settings


def generate_test_db_name() -> str:
    """
    テスト用のランダムなデータベース名を生成する。

    Returns:
        データベース名（pytest_{random_8chars}形式）
    """
    return f"pytest_{uuid.uuid4().hex[:8]}"


def get_admin_connection() -> Any:
    """
    postgres データベースへの管理者接続を取得する。

    Returns:
        psycopg2 connection オブジェクト
    """
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=int(settings.POSTGRES_PORT),
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database="postgres",  # 管理者用デフォルトDB
        gssencmode="disable",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def create_test_database(db_name: str) -> None:
    """
    テスト用データベースを作成する。

    Args:
        db_name: 作成するデータベース名
    """
    conn = get_admin_connection()
    try:
        cur = conn.cursor()
        # 既存のDBを削除（念のため）
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,),
        )
        if cur.fetchone():
            # 既存の接続を切断
            cur.execute(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid()
                """,
                (db_name,),
            )
            cur.execute(f'DROP DATABASE "{db_name}"')

        # 新規作成
        cur.execute(f'CREATE DATABASE "{db_name}"')
        cur.close()
    finally:
        conn.close()


def drop_test_database(db_name: str) -> None:
    """
    テスト用データベースを削除する。

    Args:
        db_name: 削除するデータベース名
    """
    conn = get_admin_connection()
    try:
        cur = conn.cursor()
        # 既存の接続を切断
        cur.execute(
            """
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = %s
            AND pid <> pg_backend_pid()
            """,
            (db_name,),
        )
        # DB削除
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        cur.close()
    finally:
        conn.close()


def run_migrations(database_url: str) -> None:
    """
    Alembicマイグレーションを実行する。

    Args:
        database_url: 対象データベースのURL
    """
    from pathlib import Path

    alembic_cfg = Config()

    # スクリプトディレクトリの絶対パスを設定
    # tests/helpers.py から app/infrastructure/database/alembic へのパス
    script_location = (
        Path(__file__).parent.parent / "app/infrastructure/database/alembic"
    ).resolve()
    alembic_cfg.set_main_option("script_location", str(script_location))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_cfg, "head")
