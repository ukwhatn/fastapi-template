import contextlib
import json
import logging
import os

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import api_router
from core import APIError, ErrorResponse, ValidationError, get_settings
from core.middleware import SecurityHeadersMiddleware
from utils import SessionCrud, SessionSchema

# 設定読み込み
settings = get_settings()

# アプリケーション設定
app_params = {
    "title": "FastAPI Template",
    "description": "FastAPIアプリケーションのテンプレート",
    "version": "0.1.0",
}

# ロガー設定
logging.basicConfig(level=logging.WARN)
logger = logging.getLogger("uvicorn")

if settings.is_development:
    logger.setLevel(level=logging.DEBUG)
else:
    logger.setLevel(level=logging.INFO)
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
    def filter(self, record):
        return "/system/healthcheck" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフサイクル管理
    """

    yield  # アプリケーションの実行


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
async def error_response(request: Request, call_next):
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
async def session_creator(request: Request, call_next):
    with SessionCrud() as session_crud:
        req_session_data = session_crud.get(request)
        if req_session_data is None:
            req_session_data = SessionSchema()
        request.state.session = req_session_data

    response = await call_next(request)

    with SessionCrud() as session_crud:
        res_session_data = request.state.session
        session_crud.update(request, response, res_session_data)
    return response


# 静的ファイル設定
# app.mount("/static", StaticFiles(directory="/app/static"), name="static")

# ルーター登録
app.include_router(api_router)
