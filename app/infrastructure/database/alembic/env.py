"""
Alembic環境設定

このファイルはAlembicマイグレーションを実行するための設定を提供します。
プログラム的実行とCLI実行の両方をサポートします。
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# プロジェクト設定とモデルのインポート
from app.core.config import get_settings
from app.infrastructure.database.models.base import Base

# Alembic Config object（alembic.ini から設定を読み込む際に使用）
config = context.config

# Pythonロギング設定（alembic.ini から）
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# メタデータオブジェクト（autogenerateサポート用）
target_metadata = Base.metadata

# 全てのモデルをインポート（autogenerateで検出させるため）
from app.infrastructure.database.models.session import Session  # noqa: F401, E402


def get_url() -> str:
    """
    データベースURLを取得

    プログラム的実行時は set_main_option で設定された値を使用、
    CLI実行時は環境変数から構築
    """
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    # CLI実行時は環境変数から構築
    settings = get_settings()
    return settings.database_uri


def run_migrations_offline() -> None:
    """
    'offline' モードでマイグレーションを実行

    このモードではSQLAlchemy Engineを使用せず、
    データベースURLのみを使用してSQLスクリプトを生成します。
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    'online' モードでマイグレーションを実行

    このモードではSQLAlchemy Engineを作成し、
    データベースに接続してマイグレーションを実行します。
    """
    # プログラム的実行時は外部から接続が渡される可能性を考慮
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        # 接続が渡されていない場合は新規作成
        configuration = config.get_section(config.config_ini_section) or {}
        configuration["sqlalchemy.url"] = get_url()
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
