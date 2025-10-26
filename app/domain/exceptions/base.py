"""
ドメイン層の例外クラス

ビジネスロジックで発生するエラーを表現する純粋なPython例外。
フレームワークに依存しない。
"""

from typing import Any, Optional


class DomainError(Exception):
    """
    ドメイン層のベース例外

    ビジネスロジックで発生するエラーを表現する純粋なPython例外。
    フレームワークに依存しない。

    Attributes:
        message: エラーメッセージ
        code: エラーコード（識別子）
        details: エラーの詳細情報（オプション）
    """

    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        """
        Args:
            message: エラーメッセージ
            code: エラーコード
            details: エラーの詳細情報（オプション）
        """
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)


class NotFoundError(DomainError):
    """リソースが見つからない場合のエラー"""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        """
        Args:
            message: エラーメッセージ
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message=message, code="not_found", details=details)


class BadRequestError(DomainError):
    """不正なリクエストエラー"""

    def __init__(
        self,
        message: str = "Bad request",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        """
        Args:
            message: エラーメッセージ
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message=message, code="bad_request", details=details)


class UnauthorizedError(DomainError):
    """認証エラー"""

    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        """
        Args:
            message: エラーメッセージ
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message=message, code="unauthorized", details=details)


class ForbiddenError(DomainError):
    """アクセス権限エラー"""

    def __init__(
        self,
        message: str = "Access forbidden",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        """
        Args:
            message: エラーメッセージ
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message=message, code="forbidden", details=details)


class ValidationError(BadRequestError):
    """バリデーションエラー"""

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        """
        Args:
            message: エラーメッセージ
            details: エラーの詳細情報（オプション）
                    リストまたは辞書形式で複数のバリデーションエラーを含められる
        """
        super().__init__(message=message, details=details)
        self.code = "validation_error"
