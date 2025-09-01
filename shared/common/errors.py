"""
Enhanced error handling system for LMS microservices
"""
from typing import Any, Dict, Optional, Union
from fastapi import HTTPException
from pydantic import BaseModel, Field
from shared.common.responses import ErrorResponse, ErrorCodes


class APIError(HTTPException):
    """Base API error class with standardized format"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        # Create standardized error response
        error_response = ErrorResponse.create(
            error_code=code,
            message=message,
            error_details=details,
            status_code=status_code
        )

        super().__init__(
            status_code=status_code,
            detail=error_response.dict(),
            headers=headers
        )
        self.error_code = code
        self.error_details = details


class ValidationError(APIError):
    """Validation error for input data"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {"field": field, "value": value}
        if details:
            error_details.update(details)

        super().__init__(
            status_code=422,
            code=ErrorCodes.VALIDATION_ERROR,
            message=message,
            details=error_details
        )


class NotFoundError(APIError):
    """Resource not found error"""

    def __init__(
        self,
        resource: str,
        resource_id: Union[str, int],
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {"resource": resource, "resource_id": str(resource_id)}
        if details:
            error_details.update(details)

        super().__init__(
            status_code=404,
            code=ErrorCodes.NOT_FOUND,
            message=f"{resource} with id '{resource_id}' not found",
            details=error_details
        )


class AuthorizationError(APIError):
    """Authorization error"""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=403,
            code=ErrorCodes.FORBIDDEN,
            message=message,
            details=details
        )


class AuthenticationError(APIError):
    """Authentication error"""

    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=401,
            code=ErrorCodes.UNAUTHORIZED,
            message=message,
            details=details
        )


class DatabaseError(APIError):
    """Database operation error"""

    def __init__(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {"operation": operation}
        if details:
            error_details.update(details)

        super().__init__(
            status_code=500,
            code=ErrorCodes.DATABASE_ERROR,
            message=f"Database error during {operation}: {message}",
            details=error_details
        )


class ServiceUnavailableError(APIError):
    """Service unavailable error"""

    def __init__(
        self,
        service: str,
        message: str = "Service temporarily unavailable",
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {"service": service}
        if details:
            error_details.update(details)

        super().__init__(
            status_code=503,
            code=ErrorCodes.SERVICE_UNAVAILABLE,
            message=message,
            details=error_details
        )


class RateLimitError(APIError):
    """Rate limit exceeded error"""

    def __init__(
        self,
        limit: int,
        window: int,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {"limit": limit, "window_seconds": window}
        if details:
            error_details.update(details)

        super().__init__(
            status_code=429,
            code=ErrorCodes.RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            details=error_details,
            headers={"Retry-After": str(window)}
        )


class AIError(APIError):
    """AI service error"""

    def __init__(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {"operation": operation}
        if details:
            error_details.update(details)

        super().__init__(
            status_code=500,
            code=ErrorCodes.AI_SERVICE_ERROR,
            message=f"AI service error during {operation}: {message}",
            details=error_details
        )


class ConflictError(APIError):
    """Resource conflict error"""

    def __init__(
        self,
        resource: str,
        conflict_reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = {"resource": resource, "conflict_reason": conflict_reason}
        if details:
            error_details.update(details)

        super().__init__(
            status_code=409,
            code="CONFLICT",
            message=f"Conflict with existing {resource}: {conflict_reason}",
            details=error_details
        )


class BadRequestError(APIError):
    """Bad request error"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=400,
            code="BAD_REQUEST",
            message=message,
            details=details
        )


# Error handler utilities
def handle_database_error(operation: str, error: Exception) -> DatabaseError:
    """Convert database exceptions to standardized errors"""
    return DatabaseError(operation, str(error))


def handle_validation_error(field: str, message: str, value: Any = None) -> ValidationError:
    """Create validation error with field information"""
    return ValidationError(message, field=field, value=value)


def handle_not_found(resource: str, resource_id: Union[str, int]) -> NotFoundError:
    """Create not found error"""
    return NotFoundError(resource, resource_id)


def handle_unauthorized(message: str = "Authentication required") -> AuthenticationError:
    """Create authentication error"""
    return AuthenticationError(message)


def handle_forbidden(message: str = "Insufficient permissions") -> AuthorizationError:
    """Create authorization error"""
    return AuthorizationError(message)


def handle_service_unavailable(service: str, message: Optional[str] = None) -> ServiceUnavailableError:
    """Create service unavailable error"""
    return ServiceUnavailableError(service, message or f"{service} is temporarily unavailable")


def handle_rate_limit(limit: int, window: int) -> RateLimitError:
    """Create rate limit error"""
    return RateLimitError(limit, window)


def handle_ai_error(operation: str, error: Exception) -> AIError:
    """Create AI service error"""
    return AIError(operation, str(error))


def handle_conflict(resource: str, reason: str) -> ConflictError:
    """Create conflict error"""
    return ConflictError(resource, reason)


def handle_bad_request(message: str) -> BadRequestError:
    """Create bad request error"""
    return BadRequestError(message)