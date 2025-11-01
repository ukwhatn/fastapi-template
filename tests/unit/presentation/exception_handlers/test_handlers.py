"""
Presentation層例外ハンドラーの単体テスト
"""

import asyncio
import json
from unittest.mock import MagicMock

from fastapi.exceptions import RequestValidationError

from app.domain.exceptions.base import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.presentation.exception_handlers.handlers import (
    domain_error_handler,
    validation_exception_handler,
)


class TestDomainErrorHandler:
    """domain_error_handler関数のテスト"""

    def test_not_found_error_handler(self) -> None:
        """NotFoundErrorが404レスポンスに変換されること"""
        error = NotFoundError("User not found", details={"user_id": 123})
        request = MagicMock()

        response = asyncio.run(domain_error_handler(request, error))

        assert response.status_code == 404
        content = json.loads(response.body.decode())
        assert content["status"] == "error"
        assert content["code"] == "not_found"
        assert content["message"] == "User not found"
        assert content["details"] == {"user_id": 123}

    def test_bad_request_error_handler(self) -> None:
        """BadRequestErrorが400レスポンスに変換されること"""
        error = BadRequestError("Invalid input")
        request = MagicMock()

        response = asyncio.run(domain_error_handler(request, error))

        assert response.status_code == 400
        content = json.loads(response.body.decode())
        assert content["status"] == "error"
        assert content["code"] == "bad_request"
        assert content["message"] == "Invalid input"

    def test_unauthorized_error_handler(self) -> None:
        """UnauthorizedErrorが401レスポンスに変換されること"""
        error = UnauthorizedError("Token expired")
        request = MagicMock()

        response = asyncio.run(domain_error_handler(request, error))

        assert response.status_code == 401
        content = json.loads(response.body.decode())
        assert content["status"] == "error"
        assert content["code"] == "unauthorized"
        assert content["message"] == "Token expired"

    def test_forbidden_error_handler(self) -> None:
        """ForbiddenErrorが403レスポンスに変換されること"""
        error = ForbiddenError("Insufficient permissions")
        request = MagicMock()

        response = asyncio.run(domain_error_handler(request, error))

        assert response.status_code == 403
        content = json.loads(response.body.decode())
        assert content["status"] == "error"
        assert content["code"] == "forbidden"
        assert content["message"] == "Insufficient permissions"

    def test_validation_error_handler(self) -> None:
        """ValidationErrorが400レスポンスに変換されること"""
        details: list[dict[str, str]] = [
            {"field": "email", "message": "Invalid email format"},
            {"field": "password", "message": "Password too short"},
        ]
        error = ValidationError(details=details)
        request = MagicMock()

        response = asyncio.run(domain_error_handler(request, error))

        assert response.status_code == 400
        content = json.loads(response.body.decode())
        assert content["status"] == "error"
        assert content["code"] == "validation_error"
        assert content["message"] == "Validation error"
        assert content["details"] == details


class TestValidationExceptionHandler:
    """validation_exception_handler関数のテスト"""

    def test_request_validation_error_handler(self) -> None:
        """RequestValidationErrorが適切に処理されること"""
        from pydantic_core import ErrorDetails

        # Pydantic v2のErrorDetails形式でエラーを作成
        pydantic_errors: list[ErrorDetails] = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "missing",
                "input": {},
            },  # type: ignore[typeddict-item]
            {
                "loc": ("body", "password"),
                "msg": "ensure this value has at least 8 characters",
                "type": "string_too_short",
                "input": "short",
            },  # type: ignore[typeddict-item]
        ]

        # RequestValidationErrorを作成（直接errorsパラメータを渡す）
        validation_error = RequestValidationError(errors=pydantic_errors)  # type: ignore[arg-type]

        request = MagicMock()

        response = asyncio.run(validation_exception_handler(request, validation_error))

        assert response.status_code == 400
        content = json.loads(response.body.decode())
        assert content["status"] == "error"
        assert content["code"] == "validation_error"
        assert content["message"] == "Invalid request body"
        assert isinstance(content["details"], list)
        assert len(content["details"]) == 2

    def test_validation_error_response_structure(self) -> None:
        """バリデーションエラーレスポンスの構造が正しいこと"""
        from pydantic_core import ErrorDetails

        pydantic_errors: list[ErrorDetails] = [
            {
                "loc": ("body", "username"),
                "msg": "invalid username",
                "type": "value_error",
                "input": "test",
            }  # type: ignore[typeddict-item]
        ]

        # RequestValidationErrorを作成（直接errorsパラメータを渡す）
        validation_error = RequestValidationError(errors=pydantic_errors)  # type: ignore[arg-type]

        request = MagicMock()

        response = asyncio.run(validation_exception_handler(request, validation_error))

        content = json.loads(response.body.decode())
        assert "status" in content
        assert "code" in content
        assert "message" in content
        assert "details" in content

        # details配列の各要素がloc, msg, typeを持つこと
        for detail in content["details"]:
            assert "loc" in detail
            assert "msg" in detail
            assert "type" in detail
