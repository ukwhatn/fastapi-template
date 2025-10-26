"""Domain layer - Business rules and entities"""

from .exceptions.base import (
    DomainError,
    NotFoundError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    ValidationError,
)

__all__ = [
    "DomainError",
    "NotFoundError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "ValidationError",
]
