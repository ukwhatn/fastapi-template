"""FastAPI例外ハンドラー"""

import json
from typing import Awaitable, Callable, cast

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import (
    HTTPException as FastAPIHTTPException,
    RequestValidationError,
)

from app.core import (
    APIError,
    DomainError,
    ErrorResponse,
    ValidationError,
    domain_error_to_api_error,
)


async def domain_error_handler(request: Request, exc: DomainError) -> Response:
    """DomainError例外ハンドラ"""
    api_error = domain_error_to_api_error(exc)
    return Response(
        content=json.dumps(jsonable_encoder(api_error.to_response())),
        status_code=api_error.status_code,
        media_type="application/json",
    )


async def api_error_handler(request: Request, exc: APIError) -> Response:
    """APIError例外ハンドラ（後方互換性のため保持）"""
    return Response(
        content=json.dumps(jsonable_encoder(exc.to_response())),
        status_code=exc.status_code,
        media_type="application/json",
    )


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


def register_exception_handlers(app: FastAPI) -> None:
    """
    FastAPIアプリケーションに例外ハンドラーを登録

    Args:
        app: FastAPIアプリケーションインスタンス
    """
    # 型キャスト：Starletteの型定義との互換性のため
    # FastAPIの例外ハンドラーは実行時に正しく動作するが、
    # 静的型チェッカーではStarletteの厳密な型定義に適合しない
    handler_type = Callable[[Request, Exception], Awaitable[Response]]

    app.add_exception_handler(DomainError, cast(handler_type, domain_error_handler))
    app.add_exception_handler(APIError, cast(handler_type, api_error_handler))
    app.add_exception_handler(
        FastAPIHTTPException, cast(handler_type, http_exception_handler)
    )
    app.add_exception_handler(
        RequestValidationError, cast(handler_type, validation_exception_handler)
    )
