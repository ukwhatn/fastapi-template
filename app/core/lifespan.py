"""アプリケーションライフサイクル管理"""

import contextlib
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.core.logging import get_logger
from app.presentation.static.spa import SPAStaticFiles

logger = get_logger(__name__)
settings = get_settings()

STATIC_DIR = Path(__file__).parent.parent / "static"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
FRONTEND_DIST_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"


def has_content(directory: Path) -> bool:
    """
    ディレクトリに.keep以外のファイルまたはフォルダが存在するかチェック

    Args:
        directory: チェック対象のディレクトリ

    Returns:
        .keep以外のファイル/フォルダが存在する場合True
    """
    if not directory.exists():
        return False

    for item in directory.iterdir():
        if item.name != ".keep":
            return True
    return False


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    アプリケーションのライフサイクル管理

    起動時:
    - 起動時刻の記録
    - データベースマイグレーション
    - バッチタスク登録
    - スケジューラー起動
    - 静的ファイルマウント
    - テンプレートエンジン設定
    - フロントエンドSPAマウント

    シャットダウン時:
    - スケジューラー停止

    Args:
        app: FastAPIアプリケーションインスタンス

    Yields:
        None
    """
    # 起動時刻を記録（healthcheckのuptime計算用）
    app.state.start_time = datetime.now(timezone.utc)

    # マイグレーション
    if settings.has_database:
        from app.infrastructure.database.migration import run_migrations

        run_migrations(logger_key="uvicorn")
    else:
        logger.info("Database migrations are disabled")

    # バッチタスク登録
    from app.infrastructure.batch import tasks  # タスク自動登録  # noqa: F401

    # スケジューラー起動
    from app.infrastructure.batch.scheduler import (
        create_scheduler,
        start_scheduler,
        stop_scheduler,
    )

    scheduler = create_scheduler()
    app.state.scheduler = scheduler
    start_scheduler(scheduler)

    # 静的ファイル
    if has_content(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Static files enabled: {STATIC_DIR}")
    else:
        logger.info(f"Static files disabled: {STATIC_DIR}")

    # Jinja2テンプレート
    if has_content(TEMPLATES_DIR):
        app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
        logger.info(f"Jinja2 templates enabled: {TEMPLATES_DIR}")
    else:
        logger.info(f"Jinja2 templates disabled: {TEMPLATES_DIR}")

    # フロントエンドSPA
    # テスト環境・ローカル環境ではSPAマウントを無効化（404テストを正しく動作させるため）
    if (
        not (settings.is_local or settings.is_test)
        and FRONTEND_DIST_DIR.exists()
        and FRONTEND_DIST_DIR.is_dir()
    ):
        app.mount(
            "/admin",
            SPAStaticFiles(directory=str(FRONTEND_DIST_DIR), html=True),
            name="frontend",
        )
        logger.info(f"Frontend SPA enabled at /admin: {FRONTEND_DIST_DIR}")
    else:
        if settings.is_local or settings.is_test:
            logger.info("Frontend SPA disabled: local/test mode")
        else:
            logger.info(f"Frontend SPA disabled: {FRONTEND_DIST_DIR} not found")

    yield

    # シャットダウン
    stop_scheduler(scheduler)
