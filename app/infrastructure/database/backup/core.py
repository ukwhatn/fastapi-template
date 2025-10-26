"""データベースバックアップ・リストアのコアロジック"""

from pathlib import Path

from alembic.config import Config

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

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
