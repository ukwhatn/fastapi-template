"""
Domain層例外クラスの単体テスト
"""

from typing import Any

from app.domain.exceptions.base import (
    BadRequestError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


class TestDomainError:
    """DomainError基底クラスのテスト"""

    def test_domain_error_creation(self) -> None:
        """DomainErrorを作成できること"""
        error = DomainError(
            message="Test error", code="test_error", details={"key": "value"}
        )

        assert error.message == "Test error"
        assert error.code == "test_error"
        assert error.details == {"key": "value"}
        assert str(error) == "Test error"

    def test_domain_error_without_details(self) -> None:
        """詳細情報なしでDomainErrorを作成できること"""
        error = DomainError(message="Test error", code="test_error")

        assert error.message == "Test error"
        assert error.code == "test_error"
        assert error.details is None


class TestSpecificErrors:
    """特定のドメインエラークラスのテスト"""

    def test_not_found_error(self) -> None:
        """NotFoundErrorが正しいコードを持つこと"""
        error = NotFoundError(message="User not found")

        assert error.message == "User not found"
        assert error.code == "not_found"
        assert error.details is None

    def test_not_found_error_default_message(self) -> None:
        """NotFoundErrorがデフォルトメッセージを持つこと"""
        error = NotFoundError()

        assert error.message == "Resource not found"
        assert error.code == "not_found"

    def test_bad_request_error(self) -> None:
        """BadRequestErrorが正しいコードを持つこと"""
        error = BadRequestError(message="Invalid input")

        assert error.message == "Invalid input"
        assert error.code == "bad_request"

    def test_bad_request_error_default_message(self) -> None:
        """BadRequestErrorがデフォルトメッセージを持つこと"""
        error = BadRequestError()

        assert error.message == "Bad request"
        assert error.code == "bad_request"

    def test_unauthorized_error(self) -> None:
        """UnauthorizedErrorが正しいコードを持つこと"""
        error = UnauthorizedError(message="Token expired")

        assert error.message == "Token expired"
        assert error.code == "unauthorized"

    def test_unauthorized_error_default_message(self) -> None:
        """UnauthorizedErrorがデフォルトメッセージを持つこと"""
        error = UnauthorizedError()

        assert error.message == "Authentication required"
        assert error.code == "unauthorized"

    def test_forbidden_error(self) -> None:
        """ForbiddenErrorが正しいコードを持つこと"""
        error = ForbiddenError(message="Insufficient permissions")

        assert error.message == "Insufficient permissions"
        assert error.code == "forbidden"

    def test_forbidden_error_default_message(self) -> None:
        """ForbiddenErrorがデフォルトメッセージを持つこと"""
        error = ForbiddenError()

        assert error.message == "Access forbidden"
        assert error.code == "forbidden"

    def test_validation_error_with_list_details(self) -> None:
        """ValidationErrorがリスト形式の詳細情報を持つこと"""
        details: list[dict[str, str]] = [
            {"field": "email", "message": "Invalid email format"},
            {"field": "password", "message": "Password too short"},
        ]
        error = ValidationError(details=details)

        assert error.message == "Validation error"
        assert error.code == "validation_error"
        assert error.details == details

    def test_validation_error_with_dict_details(self) -> None:
        """ValidationErrorが辞書形式の詳細情報を持つこと"""
        details: dict[str, Any] = {"field": "username", "issue": "already exists"}
        error = ValidationError(details=details)

        assert error.message == "Validation error"
        assert error.code == "validation_error"
        assert error.details == details

    def test_validation_error_default_message(self) -> None:
        """ValidationErrorがデフォルトメッセージを持つこと"""
        error = ValidationError()

        assert error.message == "Validation error"
        assert error.code == "validation_error"
        assert error.details is None


class TestErrorInheritance:
    """エラークラスの継承関係のテスト"""

    def test_validation_error_is_bad_request_error(self) -> None:
        """ValidationErrorがBadRequestErrorを継承していること"""
        error = ValidationError()

        assert isinstance(error, BadRequestError)
        assert isinstance(error, DomainError)
        assert isinstance(error, Exception)

    def test_all_errors_are_domain_errors(self) -> None:
        """すべてのエラーがDomainErrorを継承していること"""
        errors = [
            NotFoundError(),
            BadRequestError(),
            UnauthorizedError(),
            ForbiddenError(),
            ValidationError(),
        ]

        for error in errors:
            assert isinstance(error, DomainError)
            assert isinstance(error, Exception)
