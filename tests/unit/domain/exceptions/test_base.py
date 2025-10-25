"""
例外クラスの単体テスト
"""

from typing import Dict, List
from fastapi import status
from app.domain.exceptions.base import (
    APIError,
    NotFoundError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    ValidationError,
    ErrorResponse,
)


class TestAPIError:
    """APIError基底クラスのテスト"""

    def test_api_error_default(self) -> None:
        """デフォルトメッセージで例外を作成できること"""
        error = APIError()

        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.error_code == "internal_server_error"
        assert error.error_message == "Internal server error"
        assert error.details is None

    def test_api_error_custom_message(self) -> None:
        """カスタムメッセージで例外を作成できること"""
        error = APIError(message="Custom error message")

        assert error.error_message == "Custom error message"

    def test_api_error_with_details(self) -> None:
        """詳細情報を含む例外を作成できること"""
        details: Dict[str, str] = {"field": "email", "issue": "invalid format"}
        error = APIError(message="Validation failed", details=details)

        assert error.error_message == "Validation failed"
        assert error.details == details

    def test_api_error_to_response(self) -> None:
        """ErrorResponse形式に変換できること"""
        error = APIError(message="Test error", details={"key": "value"})

        response = error.to_response()

        assert isinstance(response, ErrorResponse)
        assert response.status == "error"
        assert response.code == "internal_server_error"
        assert response.message == "Test error"
        assert response.details == {"key": "value"}


class TestSpecificErrors:
    """特定のエラークラスのテスト"""

    def test_not_found_error(self) -> None:
        """NotFoundErrorが正しいステータスコードを持つこと"""
        error = NotFoundError(message="Resource not found")

        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "not_found"

    def test_bad_request_error(self) -> None:
        """BadRequestErrorが正しいステータスコードを持つこと"""
        error = BadRequestError(message="Invalid input")

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.error_code == "bad_request"

    def test_unauthorized_error(self) -> None:
        """UnauthorizedErrorが正しいステータスコードを持つこと"""
        error = UnauthorizedError(message="Authentication required")

        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.error_code == "unauthorized"

    def test_forbidden_error(self) -> None:
        """ForbiddenErrorが正しいステータスコードを持つこと"""
        error = ForbiddenError(message="Access forbidden")

        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.error_code == "forbidden"

    def test_validation_error(self) -> None:
        """ValidationErrorが正しいステータスコードを持つこと"""
        details: List[Dict[str, str]] = [
            {"field": "email", "message": "Invalid email format"},
            {"field": "password", "message": "Password too short"},
        ]
        error = ValidationError(details=details)

        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.error_code == "validation_error"
        assert error.details == details


class TestErrorResponse:
    """ErrorResponseモデルのテスト"""

    def test_error_response_basic(self) -> None:
        """基本的なErrorResponseを作成できること"""
        response = ErrorResponse(code="test_error", message="Test error message")

        assert response.status == "error"
        assert response.code == "test_error"
        assert response.message == "Test error message"
        assert response.details is None

    def test_error_response_with_details(self) -> None:
        """詳細情報を含むErrorResponseを作成できること"""
        details: Dict[str, str] = {"field": "username", "issue": "already exists"}
        response = ErrorResponse(
            code="conflict", message="Resource conflict", details=details
        )

        assert response.details == details
