"""
Custom exceptions and error handling for LMS microservices
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException
from shared.common.logging import get_logger

logger = get_logger("common-errors")

class LMSError(HTTPException):
    """Base exception for LMS errors"""

    def __init__(self, status_code: int, detail: str, error_code: Optional[str] = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or f"ERR_{status_code}"

class AuthenticationError(LMSError):
    """Authentication related errors"""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail, error_code="AUTH_001")

class AuthorizationError(LMSError):
    """Authorization related errors"""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail, error_code="AUTH_002")

class NotFoundError(LMSError):
    """Resource not found errors"""

    def __init__(self, resource: str, resource_id: Optional[str] = None):
        detail = f"{resource} not found"
        if resource_id:
            detail += f": {resource_id}"
        super().__init__(status_code=404, detail=detail, error_code="NOT_FOUND_001")

class ValidationError(LMSError):
    """Data validation errors"""

    def __init__(self, detail: str, field: Optional[str] = None):
        error_detail = f"Validation error"
        if field:
            error_detail += f" for field '{field}'"
        error_detail += f": {detail}"
        super().__init__(status_code=422, detail=error_detail, error_code="VALIDATION_001")

class DatabaseError(LMSError):
    """Database operation errors"""

    def __init__(self, operation: str, detail: str):
        super().__init__(
            status_code=500,
            detail=f"Database {operation} failed: {detail}",
            error_code="DB_001"
        )

class ExternalServiceError(LMSError):
    """External service communication errors"""

    def __init__(self, service: str, operation: str, detail: str):
        super().__init__(
            status_code=502,
            detail=f"External service '{service}' {operation} failed: {detail}",
            error_code="EXT_SVC_001"
        )

class RateLimitError(LMSError):
    """Rate limiting errors"""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail, error_code="RATE_LIMIT_001")

class BusinessLogicError(LMSError):
    """Business logic violation errors"""

    def __init__(self, detail: str, error_code: str = "BUSINESS_001"):
        super().__init__(status_code=400, detail=detail, error_code=error_code)

# Specific business errors
class CourseNotEnrolledError(BusinessLogicError):
    """User not enrolled in course"""

    def __init__(self, course_id: str):
        super().__init__(
            detail=f"Not enrolled in course: {course_id}",
            error_code="COURSE_001"
        )

class AssignmentAlreadySubmittedError(BusinessLogicError):
    """Assignment already submitted"""

    def __init__(self, assignment_id: str):
        super().__init__(
            detail=f"Assignment already submitted: {assignment_id}",
            error_code="ASSIGNMENT_001"
        )

class QuizTimeExpiredError(BusinessLogicError):
    """Quiz time has expired"""

    def __init__(self, quiz_id: str):
        super().__init__(
            detail=f"Quiz time has expired: {quiz_id}",
            error_code="QUIZ_001"
        )

def handle_error(error: Exception, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """Convert exception to standardized error response"""
    if isinstance(error, LMSError):
        logger.error(
            f"LMS Error: {error.detail}",
            extra={
                "error_code": error.error_code,
                "status_code": error.status_code,
                "correlation_id": correlation_id
            },
            correlation_id=correlation_id
        )
        return {
            "error": {
                "code": error.error_code,
                "message": error.detail,
                "status_code": error.status_code
            }
        }
    elif isinstance(error, HTTPException):
        logger.error(
            f"HTTP Error: {error.detail}",
            extra={
                "status_code": error.status_code,
                "correlation_id": correlation_id
            },
            correlation_id=correlation_id
        )
        return {
            "error": {
                "code": f"HTTP_{error.status_code}",
                "message": error.detail,
                "status_code": error.status_code
            }
        }
    else:
        # Generic error
        logger.error(
            f"Unexpected error: {str(error)}",
            extra={
                "error_type": type(error).__name__,
                "correlation_id": correlation_id
            },
            correlation_id=correlation_id
        )
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "status_code": 500
            }
        }