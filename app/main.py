import contextlib
import json
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, AsyncIterator, MutableMapping

import newrelic.agent
import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import (
    HTTPException as FastAPIHTTPException,
    RequestValidationError,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .core import (
    APIError,
    DomainError,
    ErrorResponse,
    ValidationError,
    domain_error_to_api_error,
    get_settings,
)
from .core.logging import get_logger
from .infrastructure.batch.scheduler import (
    create_scheduler,
    start_scheduler,
    stop_scheduler,
)
from .infrastructure.database import get_db
from .infrastructure.repositories.session_repository import SessionService
from .presentation import api_router
from .presentation.middleware.security_headers import SecurityHeadersMiddleware

APP_PARAMS: dict[str, Any] = {
    "title": "FastAPI Template",
    "description": "FastAPIアプリケーションのテンプレート",
    "version": "0.1.0",
}

SETTINGS = get_settings()

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"
FRONTEND_DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    """
    SPA対応の静的ファイルサーバー

    404エラーが発生した場合にindex.htmlを返すことで、
    React Routerのhistory modeをサポート
    """

    async def get_response(
        self, path: str, scope: MutableMapping[str, Any]
    ) -> Response:
        try:
            return await super().get_response(path, scope)
        except FastAPIHTTPException as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise ex


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/system/healthcheck" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

logger = get_logger(__name__)


# 本番環境ではドキュメントを無効化
if SETTINGS.is_production:
    APP_PARAMS["docs_url"] = None
    APP_PARAMS["redoc_url"] = None
    APP_PARAMS["openapi_url"] = None

if SETTINGS.is_production and SETTINGS.NEW_RELIC_LICENSE_KEY:
    os.environ["NEW_RELIC_LICENSE_KEY"] = SETTINGS.NEW_RELIC_LICENSE_KEY
    os.environ["NEW_RELIC_APP_NAME"] = SETTINGS.NEW_RELIC_APP_NAME

    newrelic_config = newrelic.agent.global_settings()
    newrelic_config.high_security = SETTINGS.NEW_RELIC_HIGH_SECURITY
    newrelic_config.monitor_mode = SETTINGS.NEW_RELIC_MONITOR_MODE
    newrelic_config.app_name = (
        f"{SETTINGS.NEW_RELIC_APP_NAME}[{SETTINGS.normalized_env_mode}]"
    )

    newrelic.agent.initialize(
        config_file="/etc/newrelic.ini", environment=SETTINGS.ENV_MODE
    )
    logger.info(f"New Relic is enabled (name: {newrelic_config.app_name})")
else:
    logger.info(
        f"New Relic is disabled on {SETTINGS.ENV_MODE} mode"
        if not SETTINGS.is_production
        else "New Relic license key is not set"
    )

if SETTINGS.SENTRY_DSN:
    sentry_sdk.init(
        dsn=SETTINGS.SENTRY_DSN,
        environment=SETTINGS.normalized_env_mode,
        traces_sample_rate=SETTINGS.SENTRY_TRACES_SAMPLE_RATE,
        _experiments={
            "continuous_profiling_auto_start": True,
        },
    )
    logger.info(f"Sentry is enabled on {SETTINGS.normalized_env_mode} mode")
else:
    logger.info(
        f"Sentry is disabled on {SETTINGS.normalized_env_mode} mode"
        if not SETTINGS.is_production
        else "Sentry DSN is not set"
    )


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
    if SETTINGS.has_database:
        from .infrastructure.database.migration import run_migrations

        run_migrations(logger_key="uvicorn")
    else:
        logger.info("Database migrations are disabled")

    from .infrastructure.batch import tasks  # タスク自動登録  # noqa: F401

    scheduler = create_scheduler()
    app.state.scheduler = scheduler
    start_scheduler(scheduler)

    if has_content(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Static files enabled: {STATIC_DIR}")
    else:
        logger.info(f"Static files disabled: {STATIC_DIR}")

    if has_content(TEMPLATES_DIR):
        app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
        logger.info(f"Jinja2 templates enabled: {TEMPLATES_DIR}")
    else:
        logger.info(f"Jinja2 templates disabled: {TEMPLATES_DIR}")

    # テスト環境・ローカル環境ではSPAマウントを無効化（404テストを正しく動作させるため）
    if (
        not (SETTINGS.is_local or SETTINGS.is_test)
        and FRONTEND_DIST_DIR.exists()
        and FRONTEND_DIST_DIR.is_dir()
    ):
        app.mount(
            "/",
            SPAStaticFiles(directory=str(FRONTEND_DIST_DIR), html=True),
            name="frontend",
        )
        logger.info(f"Frontend SPA enabled: {FRONTEND_DIST_DIR}")
    else:
        if SETTINGS.is_local or SETTINGS.is_test:
            logger.info("Frontend SPA disabled: local/test mode")
        else:
            logger.info(f"Frontend SPA disabled: {FRONTEND_DIST_DIR} not found")

    yield

    stop_scheduler(scheduler)


APP_PARAMS["lifespan"] = lifespan

app = FastAPI(**APP_PARAMS)

if len(SETTINGS.BACKEND_CORS_ORIGINS) > 0:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in SETTINGS.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> Response:
    """DomainError例外ハンドラ"""
    api_error = domain_error_to_api_error(exc)
    return Response(
        content=json.dumps(jsonable_encoder(api_error.to_response())),
        status_code=api_error.status_code,
        media_type="application/json",
    )


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> Response:
    """APIError例外ハンドラ（後方互換性のため保持）"""
    return Response(
        content=json.dumps(jsonable_encoder(exc.to_response())),
        status_code=exc.status_code,
        media_type="application/json",
    )


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(
    request: Request, exc: FastAPIHTTPException
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
    """バリデーションエラーハンドラ（Pydantic）"""
    error = ValidationError(
        message="Invalid request body",
        details=[
            {"loc": err["loc"], "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ],
    )
    api_error = domain_error_to_api_error(error)
    return Response(
        content=json.dumps(jsonable_encoder(api_error.to_response())),
        status_code=api_error.status_code,
        media_type="application/json",
    )


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


@app.middleware("http")
async def session_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    セッション管理ミドルウェア

    DATABASE_URLが設定されている場合のみ、RDBベースのセッション管理を有効化
    """
    if SETTINGS.has_database:
        db_gen = get_db()
        db = next(db_gen)
        try:
            session_id = request.cookies.get(SETTINGS.SESSION_COOKIE_NAME)
            if session_id:
                service = SessionService(db)
                user_agent = request.headers.get("User-Agent")
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

            response = await call_next(request)

            # セッションデータの永続化は各エンドポイントで明示的に実施
            # ミドルウェアでの自動保存は行わない（パフォーマンス対策）

            return response
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    else:
        request.state.session = None
        return await call_next(request)


app.include_router(api_router)
