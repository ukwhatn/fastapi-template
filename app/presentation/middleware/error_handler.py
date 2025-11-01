"""エラーハンドリングミドルウェア"""

import json
from collections.abc import Awaitable, Callable

import sentry_sdk
from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder

from app.core import ErrorResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


async def error_response_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    全ての未処理例外をキャッチしてJSON形式で返す

    Args:
        request: HTTPリクエスト
        call_next: 次のミドルウェア/エンドポイント

    Returns:
        HTTPレスポンス
    """
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
