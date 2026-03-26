"""Core module - Settings and cross-cutting concerns"""

# Domain層のエラー
from ..domain.exceptions.base import (
    BadRequestError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)

# Presentation層のエラー
from ..presentation.exceptions import (
    APIError,
    ErrorResponse,
    domain_error_to_api_error,
)
from .config import Settings, get_settings

__all__ = [
    "APIError",
    "BadRequestError",
    "DomainError",
    "ErrorResponse",
    "ForbiddenError",
    "NotFoundError",
    "Settings",
    "UnauthorizedError",
    "ValidationError",
    "domain_error_to_api_error",
    "get_settings",
]
