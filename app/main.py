import json
import logging

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core import get_settings
from app.utils import SessionCrud, SessionSchema

# 設定読み込み
settings = get_settings()

# ロガー設定
logging.basicConfig(level=logging.WARN)
logger = logging.getLogger("uvicorn")

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

# 環境に合わせたアプリケーション設定
app_params = {}
if settings.ENV_MODE == "development":
    logger.setLevel(level=logging.DEBUG)
else:
    logger.setLevel(level=logging.INFO)
    # 本番環境ではドキュメントを無効化
    if settings.ENV_MODE == "production":
        app_params["docs_url"] = None
        app_params["redoc_url"] = None
        app_params["openapi_url"] = None

# アプリケーション作成
app = FastAPI(**app_params)

# CORSミドルウェア設定
# origins = [
#     "http://example.com",
# ]
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# エラーハンドリングミドルウェア
@app.middleware("http")
def error_response(request: Request, call_next):
    response = Response(
        json.dumps({"status": "internal server error"}), status_code=500
    )
    try:
        response = call_next(request)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(e)
    return response


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