# app/core/exceptions.py
"""
Custom Exceptions and Exception Handlers
=========================================
WHY custom exceptions?
----------------------
FastAPI converts unhandled exceptions into 500 Internal Server Error responses
with a generic body. That's bad for API consumers because:

1. They can't distinguish "document not found" from "database is down"
2. They can't machine-parse the error (e.g., display a user-friendly message)
3. You expose internal stack traces accidentally

By defining our own exception hierarchy and registering FastAPI exception
handlers, we get:
- Predictable JSON error responses
- Correct HTTP status codes
- A single place to add logging/alerting for specific error types

Design pattern — Exception hierarchy:
--------------------------------------
AppException (base)
├── NotFoundError       → 404
├── ValidationError     → 422 (FastAPI already handles Pydantic's, this is ours)
├── ConflictError       → 409 (e.g., duplicate document)
├── ProcessingError     → 500 (document parsing failed)
└── ServiceUnavailable  → 503 (external API down)
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# =============================================================================
# Exception classes
# =============================================================================


class AppException(Exception):
    """
    Base exception for all application-level errors.

    Every custom exception carries:
    - status_code: the HTTP status code to return
    - detail:      human-readable message for the API consumer
    - code:        machine-readable error code for programmatic handling
    """

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppException):
    """Resource does not exist (404)."""

    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppException):
    """Resource already exists / state conflict (409)."""

    status_code = 409
    code = "CONFLICT"


class ValidationError(AppException):
    """Business-level validation failure (422)."""

    status_code = 422
    code = "VALIDATION_ERROR"


class ProcessingError(AppException):
    """Document or pipeline processing failed (500)."""

    status_code = 500
    code = "PROCESSING_ERROR"


class ServiceUnavailableError(AppException):
    """External dependency (LLM, DB) is unreachable (503)."""

    status_code = 503
    code = "SERVICE_UNAVAILABLE"


# =============================================================================
# FastAPI exception handlers
# =============================================================================


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Catch any AppException subclass and return a structured JSON error.

    The response body always looks like:
    {
        "error": {
            "code":    "NOT_FOUND",
            "message": "Document abc123 not found",
            "status":  404
        }
    }

    This consistent envelope makes it easy for frontend code and API consumers
    to handle errors uniformly.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.detail,
                "status": exc.status_code,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for any exception we didn't anticipate.

    IMPORTANT: Never leak the raw exception message to the client in production.
    In debug mode we include it to help during development.
    """
    # Import here to avoid circular import
    from app.core.config import get_settings
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)

    settings = get_settings()
    message = str(exc) if settings.debug else "An unexpected error occurred. Please try again."

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": message,
                "status": 500,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI app.

    Called once during application startup in main.py.
    """
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
