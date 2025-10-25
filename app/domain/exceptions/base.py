from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """
    標準エラーレスポンス
    """

    status: str = "error"
    code: str
    message: str
    details: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None


class APIError(HTTPException):
    """
    API エラーの基底クラス
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_server_error"
    error_message: str = "Internal server error"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    ):
        self.error_message = message or self.error_message
        self.details = details
        super().__init__(status_code=self.status_code, detail=self.error_message)

    def to_response(self) -> ErrorResponse:
        """
        標準エラーレスポンス形式に変換
        """
        return ErrorResponse(
            code=self.error_code, message=self.error_message, details=self.details
        )


class NotFoundError(APIError):
    """
    リソースが見つからない場合のエラー
    """

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    error_message = "Resource not found"


class BadRequestError(APIError):
    """
    不正なリクエストエラー
    """

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"
    error_message = "Bad request"


class UnauthorizedError(APIError):
    """
    認証エラー
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"
    error_message = "Authentication required"


class ForbiddenError(APIError):
    """
    アクセス権限エラー
    """

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"
    error_message = "Access forbidden"


class ValidationError(BadRequestError):
    """
    バリデーションエラー
    """

    error_code = "validation_error"
    error_message = "Validation error"
