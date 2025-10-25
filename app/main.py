import contextlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, AsyncIterator
from collections.abc import Callable, Awaitable

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from .presentation import api_router
from .core import APIError, ErrorResponse, ValidationError, get_settings
from .core.logging import get_logger
from .presentation.middleware.security_headers import SecurityHeadersMiddleware
from .infrastructure.database import get_db
from .infrastructure.repositories.session_repository import SessionService

# 設定読み込み
settings = get_settings()

# ディレクトリパス設定
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# アプリケーション設定
app_params: Dict[str, Any] = {
    "title": "FastAPI Template",
    "description": "FastAPIアプリケーションのテンプレート",
    "version": "0.1.0",
}

# ロガー設定
logger = get_logger(__name__)

# 本番環境ではドキュメントを無効化
if settings.is_production:
    app_params["docs_url"] = None
    app_params["redoc_url"] = None
    app_params["openapi_url"] = None

# New Relic設定
if settings.is_production and settings.NEW_RELIC_LICENSE_KEY:
    print("New Relic!")
    import newrelic.agent

    # 環境変数のオーバーライド
    os.environ["NEW_RELIC_LICENSE_KEY"] = settings.NEW_RELIC_LICENSE_KEY
    os.environ["NEW_RELIC_APP_NAME"] = settings.NEW_RELIC_APP_NAME

    # 設定オブジェクトの作成
    newrelic_config = newrelic.agent.global_settings()
    newrelic_config.high_security = settings.NEW_RELIC_HIGH_SECURITY
    newrelic_config.monitor_mode = settings.NEW_RELIC_MONITOR_MODE
    newrelic_config.app_name = settings.NEW_RELIC_APP_NAME

    # New Relic初期化
    newrelic.agent.initialize(
        config_file="/etc/newrelic.ini", environment=settings.ENV_MODE
    )
    logger.info("New Relic is enabled")
else:
    logger.info(
        f"New Relic is disabled on {settings.ENV_MODE} mode"
        if not settings.is_production
        else "New Relic license key is not set"
    )

# Sentry設定
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        _experiments={
            "continuous_profiling_auto_start": True,
        },
    )


# ヘルスチェックフィルター
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/system/healthcheck" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


def has_content(directory: Path) -> bool:
    """ディレクトリに.keep以外のファイルまたはフォルダが存在するかチェック"""
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
    """
    # データベースマイグレーション実行
    if settings.has_database:
        from .infrastructure.database.migration import run_migrations

        run_migrations(logger_key="uvicorn")
    else:
        logger.info("Database migrations are disabled")

    # バッチスケジューラー起動
    from .infrastructure.batch.scheduler import (
        create_scheduler,
        start_scheduler,
        stop_scheduler,
    )
    from .infrastructure.batch import tasks  # タスク自動登録  # noqa: F401

    scheduler = create_scheduler()
    app.state.scheduler = scheduler
    start_scheduler(scheduler)

    # 静的ファイルとテンプレートの自動設定
    if has_content(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Static files enabled: {STATIC_DIR}")
    else:
        logger.info(f"Static files disabled: {STATIC_DIR}")

    if has_content(TEMPLATES_DIR):
        # Jinja2Templatesインスタンスをアプリケーション状態に保存
        app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
        logger.info(f"Jinja2 templates enabled: {TEMPLATES_DIR}")
    else:
        logger.info(f"Jinja2 templates disabled: {TEMPLATES_DIR}")

    yield  # アプリケーションの実行

    # バッチスケジューラー停止
    stop_scheduler(scheduler)


app_params["lifespan"] = lifespan

# アプリケーション作成
app = FastAPI(**app_params)

# CORSミドルウェア設定
if len(settings.BACKEND_CORS_ORIGINS) > 0:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# セキュリティヘッダーミドルウェア追加
app.add_middleware(SecurityHeadersMiddleware)


# カスタムエラーハンドラ
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> Response:
    """APIError例外ハンドラ"""
    return Response(
        content=json.dumps(jsonable_encoder(exc.to_response())),
        status_code=exc.status_code,
        media_type="application/json",
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> Response:
    """HTTPException例外ハンドラ"""
    error = ErrorResponse(
        code="http_error",
        message=str(exc.detail),
    )
    return Response(
        content=json.dumps(jsonable_encoder(error)),
        status_code=exc.status_code,
        media_type="application/json",
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    """バリデーションエラーハンドラ"""
    error = ValidationError(
        message="Invalid request body",
        details=[
            {"loc": err["loc"], "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ],
    )
    return Response(
        content=json.dumps(jsonable_encoder(error.to_response())),
        status_code=error.status_code,
        media_type="application/json",
    )


# エラーハンドリングミドルウェア
@app.middleware("http")
async def error_response(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Unhandled exception: {str(e)}", exc_info=e)

        error = ErrorResponse(
            code="internal_server_error",
            message="Internal server error occurred",
        )
        return Response(
            content=json.dumps(jsonable_encoder(error)),
            status_code=500,
            media_type="application/json",
        )


# セッション管理ミドルウェア
@app.middleware("http")
async def session_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    セッション管理ミドルウェア

    DATABASE_URLが設定されている場合のみ、RDBベースのセッション管理を有効化
    """
    if settings.has_database:
        # データベースセッション取得
        db_gen = get_db()
        db = next(db_gen)
        try:
            # セッションIDをCookieから取得
            session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
            if session_id:
                # 既存セッション取得
                service = SessionService(db)
                # UA取得
                user_agent = request.headers.get("User-Agent")
                # IP取得
                client_ip_headers = ["CF-Connecting-IP", "X-Forwarded-For"]
                client_ip = None
                for header in client_ip_headers:
                    client_ip = request.headers.get(header)
                    if client_ip:
                        break
                if not client_ip:
                    client_ip = request.client.host if request.client else None

                session_data = service.get_session(session_id, user_agent, client_ip)

                request.state.session = session_data or {}
                request.state.session_id = session_id
                request.state.client_ip = client_ip
                request.state.user_agent = user_agent
            else:
                request.state.session = {}

            # リクエスト処理
            response = await call_next(request)

            # セッションデータの永続化は各エンドポイントで明示的に実施
            # ミドルウェアでの自動保存は行わない（パフォーマンス対策）

            return response
        finally:
            # DBセッションクローズ
            try:
                next(db_gen)
            except StopIteration:
                pass
    else:
        # データベース未設定時はセッション無効
        request.state.session = None
        return await call_next(request)


# ルーター登録
app.include_router(api_router)
