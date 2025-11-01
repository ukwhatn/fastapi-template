"""FastAPIアプリケーションファクトリー"""

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.lifespan import lifespan
from app.core.logging import get_logger
from app.presentation import api_router
from app.presentation.exception_handlers import register_exception_handlers
from app.presentation.middleware.error_handler import error_response_middleware
from app.presentation.middleware.security_headers import SecurityHeadersMiddleware
from app.presentation.middleware.session import session_middleware

logger = get_logger(__name__)


class HealthCheckFilter(logging.Filter):
    """ヘルスチェックログを除外するフィルター"""

    def filter(self, record: logging.LogRecord) -> bool:
        """
        ログレコードをフィルタリング

        Args:
            record: ログレコード

        Returns:
            ログを出力する場合True、除外する場合False
        """
        return "/api/system/healthcheck" not in record.getMessage()


def create_app() -> FastAPI:
    """
    FastAPIアプリケーションを生成

    Returns:
        FastAPIアプリケーションインスタンス
    """
    settings = get_settings()

    # アプリケーションパラメータ
    app_params: dict[str, Any] = {
        "title": "FastAPI Template",
        "description": "FastAPIアプリケーションのテンプレート",
        "version": "0.1.0",
        "lifespan": lifespan,
    }

    # 本番環境ではドキュメントを無効化
    if settings.is_production:
        app_params["docs_url"] = None
        app_params["redoc_url"] = None
        app_params["openapi_url"] = None

    # アプリ生成
    app = FastAPI(**app_params)

    # ヘルスチェックログフィルター
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    # CORS
    if len(settings.BACKEND_CORS_ORIGINS) > 0:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # セキュリティヘッダー
    app.add_middleware(SecurityHeadersMiddleware)

    # 例外ハンドラー登録
    register_exception_handlers(app)

    # ミドルウェア登録
    app.middleware("http")(error_response_middleware)
    app.middleware("http")(session_middleware)

    # ルーター登録
    app.include_router(api_router)

    # ルートリダイレクト
    @app.get("/")
    async def root_redirect() -> RedirectResponse:
        """ルートパスから/adminへリダイレクト"""
        return RedirectResponse(url="/admin/")

    return app
