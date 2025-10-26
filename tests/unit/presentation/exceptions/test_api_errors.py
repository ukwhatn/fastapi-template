"""
Presentation層APIエラークラスの単体テスト
"""

from fastapi import status

from app.domain.exceptions.base import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.presentation.exceptions import (
    APIError,
    ErrorResponse,
    domain_error_to_api_error,
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
        details: dict[str, str] = {"field": "email", "issue": "invalid format"}
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
        details: dict[str, str] = {"field": "username", "issue": "already exists"}
        response = ErrorResponse(
            code="conflict", message="Resource conflict", details=details
        )

        assert response.details == details


class TestDomainErrorToAPIError:
    """domain_error_to_api_error関数のテスト"""

    def test_not_found_error_conversion(self) -> None:
        """NotFoundErrorが404に変換されること"""
        domain_error = NotFoundError("User not found")
        api_error = domain_error_to_api_error(domain_error)

        assert api_error.status_code == status.HTTP_404_NOT_FOUND
        assert api_error.error_code == "not_found"
        assert api_error.error_message == "User not found"

    def test_bad_request_error_conversion(self) -> None:
        """BadRequestErrorが400に変換されること"""
        domain_error = BadRequestError("Invalid input")
        api_error = domain_error_to_api_error(domain_error)

        assert api_error.status_code == status.HTTP_400_BAD_REQUEST
        assert api_error.error_code == "bad_request"
        assert api_error.error_message == "Invalid input"

    def test_unauthorized_error_conversion(self) -> None:
        """UnauthorizedErrorが401に変換されること"""
        domain_error = UnauthorizedError("Token expired")
        api_error = domain_error_to_api_error(domain_error)

        assert api_error.status_code == status.HTTP_401_UNAUTHORIZED
        assert api_error.error_code == "unauthorized"
        assert api_error.error_message == "Token expired"

    def test_forbidden_error_conversion(self) -> None:
        """ForbiddenErrorが403に変換されること"""
        domain_error = ForbiddenError("Insufficient permissions")
        api_error = domain_error_to_api_error(domain_error)

        assert api_error.status_code == status.HTTP_403_FORBIDDEN
        assert api_error.error_code == "forbidden"
        assert api_error.error_message == "Insufficient permissions"

    def test_validation_error_conversion(self) -> None:
        """ValidationErrorが400に変換されること"""
        details: list[dict[str, str]] = [
            {"field": "email", "message": "Invalid email format"},
        ]
        domain_error = ValidationError(details=details)
        api_error = domain_error_to_api_error(domain_error)

        assert api_error.status_code == status.HTTP_400_BAD_REQUEST
        assert api_error.error_code == "validation_error"
        assert api_error.error_message == "Validation error"
        assert api_error.details == details

    def test_error_with_details_conversion(self) -> None:
        """詳細情報を持つエラーが正しく変換されること"""
        details = {"field": "username", "issue": "already exists"}
        domain_error = NotFoundError("Resource not found", details=details)
        api_error = domain_error_to_api_error(domain_error)

        assert api_error.details == details

    def test_api_error_to_response(self) -> None:
        """変換されたAPIErrorがto_responseを呼べること"""
        domain_error = NotFoundError("User not found")
        api_error = domain_error_to_api_error(domain_error)
        response = api_error.to_response()

        assert isinstance(response, ErrorResponse)
        assert response.code == "not_found"
        assert response.message == "User not found"
