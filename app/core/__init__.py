"""Core module - Settings and cross-cutting concerns"""

from .config import Settings, get_settings

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

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # Domain errors
    "DomainError",
    "NotFoundError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "ValidationError",
    # Presentation errors (for API layer)
    "ErrorResponse",
    "APIError",
    "domain_error_to_api_error",
]
