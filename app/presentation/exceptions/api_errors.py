"""
Presentation層のAPIエラークラス

FastAPI/Pydanticに依存するAPIエラークラス。
ドメインエラーをHTTPレスポンスに変換する。
"""

from typing import Any, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel

from ...domain.exceptions.base import (
    BadRequestError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


class ErrorResponse(BaseModel):
    """
    標準エラーレスポンス

    API呼び出し時のエラーレスポンス形式を定義する。

    Attributes:
        status: ステータス（常に"error"）
        code: エラーコード
        message: エラーメッセージ
        details: エラーの詳細情報（オプション）
    """

    status: str = "error"
    code: str
    message: str
    details: Optional[list[dict[str, Any]] | dict[str, Any]] = None


class APIError(HTTPException):
    """
    API エラーの基底クラス

    FastAPIのHTTPExceptionを継承し、ドメインエラーを
    HTTPレスポンスに変換する。

    Attributes:
        status_code: HTTPステータスコード
        error_code: エラーコード
        error_message: エラーメッセージ
        details: エラーの詳細情報
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_server_error"
    error_message: str = "Internal server error"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[list[dict[str, Any]] | dict[str, Any]] = None,
    ) -> None:
        """
        Args:
            message: エラーメッセージ（オプション）
            details: エラーの詳細情報（オプション）
        """
        self.error_message = message or self.error_message
        self.details = details
        super().__init__(status_code=self.status_code, detail=self.error_message)

    def to_response(self) -> ErrorResponse:
        """
        標準エラーレスポンス形式に変換

        Returns:
            ErrorResponse: 標準エラーレスポンス
        """
        return ErrorResponse(
            code=self.error_code, message=self.error_message, details=self.details
        )


def domain_error_to_api_error(domain_error: DomainError) -> APIError:
    """
    ドメインエラーをAPIエラーに変換

    ドメイン層の例外をPresentation層のHTTP例外に変換する。
    エラーの種類に応じて適切なHTTPステータスコードを設定する。

    Args:
        domain_error: ドメイン層のエラー

    Returns:
        APIError: API層のエラー

    Examples:
        >>> from app.domain.exceptions.base import NotFoundError
        >>> domain_err = NotFoundError("User not found")
        >>> api_err = domain_error_to_api_error(domain_err)
        >>> api_err.status_code
        404
    """
    # エラータイプに応じたHTTPステータスコードのマッピング
    status_map: dict[type, int] = {
        NotFoundError: status.HTTP_404_NOT_FOUND,
        BadRequestError: status.HTTP_400_BAD_REQUEST,
        UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
        ForbiddenError: status.HTTP_403_FORBIDDEN,
        ValidationError: status.HTTP_400_BAD_REQUEST,
    }

    # ステータスコードを決定
    status_code = status_map.get(
        type(domain_error), status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # APIErrorを生成
    api_error = APIError(
        message=domain_error.message,
        details=domain_error.details,
    )
    api_error.status_code = status_code
    api_error.error_code = domain_error.code
    api_error.error_message = domain_error.message

    return api_error
