"""Custom error classes and error handlers for the application."""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from structlog import get_logger

logger = get_logger()


class AppError(Exception):
    """Base exception class for application errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)


class ValidationError(AppError):
    """Exception raised for validation errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class NotFoundError(AppError):
    """Exception raised when a resource is not found."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(AppError):
    """Exception raised for conflicts (e.g., duplicate resources)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_409_CONFLICT,
        )


class RateLimitError(AppError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class ExternalServiceError(AppError):
    """Exception raised when an external service fails."""

    def __init__(
        self,
        message: str,
        service_name: str,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        details["service"] = service_name
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class CodebaseProcessingError(AppError):
    """Exception raised when codebase processing fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class QueryError(AppError):
    """Exception raised when query processing fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle custom application errors."""
    logger.warning(
        "application_error",
        path=request.url.path,
        error_type=type(exc).__name__,
        message=exc.message,
        details=exc.details,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "type": type(exc).__name__,
                "details": exc.details,
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        "http_exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "HTTPException",
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error_type=type(exc).__name__,
        message=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "An unexpected error occurred",
                "type": "InternalServerError",
            }
        },
    )
