"""
データベースマイグレーション実行モジュール

FastAPIアプリケーション起動時にAlembicマイグレーションを
プログラム的に実行するための機能を提供します。
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import Settings, get_settings
from app.core.logging import get_logger


def _configure_migration_logging(settings: Settings) -> None:
    """
    マイグレーション用のロガーを設定する。

    Alembic/SQLAlchemyのロガーをuvicornロガーに統合し、
    環境に応じた適切なログレベルを設定する。

    Args:
        settings: アプリケーション設定
    """
    uvicorn_logger = logging.getLogger("uvicorn")

    # Alembicロガーの設定（uvicornロガーに統合）
    alembic_logger = logging.getLogger("alembic")
    for handler in uvicorn_logger.handlers:
        alembic_logger.addHandler(handler)

    # 環境に応じてログレベルを設定
    if settings.is_staging:
        alembic_logger.setLevel(logging.DEBUG)  # 開発環境: 詳細ログ
    else:
        alembic_logger.setLevel(logging.INFO)  # 本番環境: 基本情報のみ

    # SQLAlchemyロガーの設定（マイグレーション時のSQL文表示用）
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    for handler in uvicorn_logger.handlers:
        sqlalchemy_logger.addHandler(handler)

    if settings.is_staging:
        sqlalchemy_logger.setLevel(logging.INFO)  # 開発環境: SQL文を表示
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)  # 本番環境: 警告のみ


def _create_alembic_config(settings: Settings) -> Config:
    """
    Alembic設定オブジェクトを作成する。

    Args:
        settings: アプリケーション設定

    Returns:
        Config: Alembic設定オブジェクト
    """
    alembic_cfg = Config()

    # スクリプトディレクトリの絶対パスを設定
    script_location = (Path(__file__).parent / "alembic").resolve()
    alembic_cfg.set_main_option("script_location", str(script_location))

    # データベースURLを設定
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_uri)

    return alembic_cfg


def run_migrations(logger_key: str | None = None) -> None:
    """
    データベースマイグレーションを実行

    Alembicを使用してデータベースを最新の状態に更新します。
    マイグレーションが失敗した場合は例外をraiseし、
    アプリケーション起動を停止します。

    Raises:
        RuntimeError: マイグレーション実行に失敗した場合
    """
    logger = get_logger(logger_key or __name__)
    try:
        settings = get_settings()

        # マイグレーション用のロガー設定
        _configure_migration_logging(settings)

        # Alembic設定を作成
        alembic_cfg = _create_alembic_config(settings)

        # マイグレーション開始ログ
        script_location = (Path(__file__).parent / "alembic").resolve()
        logger.info("Starting database migrations...")
        logger.info(f"Script location: {script_location}")
        logger.info(
            f"Database: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )

        # マイグレーション実行（head = 最新バージョン）
        command.upgrade(alembic_cfg, "head")

        logger.info("Database migrations completed successfully")

    except Exception as e:
        logger.error(f"Database migration failed: {e}", exc_info=True)
        # マイグレーション失敗時は起動を停止
        raise RuntimeError(f"Database migration failed: {e}") from e
