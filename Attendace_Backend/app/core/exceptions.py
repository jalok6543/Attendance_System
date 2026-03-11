"""Custom exceptions and exception handlers."""

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppException):
    """User not authorized for this action."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(AppException):
    """Validation failed."""

    def __init__(self, message: str = "Validation failed", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)


class DuplicateError(AppException):
    """Duplicate resource."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class FaceRecognitionError(AppException):
    """Face recognition failed."""

    def __init__(self, message: str = "Face recognition failed"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class DuplicateFaceError(AppException):
    """Face already registered under another student."""

    def __init__(self, message: str = "This face is already registered in the system.", similarity: float | None = None):
        details = {"status": "duplicate_face"}
        if similarity is not None:
            details["similarity"] = round(similarity, 4)
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, details=details)


class LivenessError(AppException):
    """Liveness detection failed."""

    def __init__(self, message: str = "Liveness verification failed"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    from app.core.config import get_settings
    settings = get_settings()
    msg = str(exc) if settings.DEBUG else "An unexpected error occurred"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": msg,
            "details": {},
        },
    )
