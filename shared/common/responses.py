"""
Standardized API Response formats for LMS microservices
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class APIResponse(BaseModel):
    """Standard API response format"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginatedResponse(APIResponse):
    """Paginated API response format"""
    data: List[Any] = Field(default_factory=list)
    pagination: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        data: List[Any],
        page: int = 1,
        limit: int = 20,
        total: int = 0,
        message: Optional[str] = None
    ) -> 'PaginatedResponse':
        total_pages = (total + limit - 1) // limit if total > 0 else 1

        return cls(
            success=True,
            data=data,
            message=message,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        )


class ErrorResponse(APIResponse):
    """Error response format"""
    success: bool = False
    error_code: str
    error_details: Optional[Dict[str, Any]] = None

    @classmethod
    def create(
        cls,
        error_code: str,
        message: str,
        error_details: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ) -> 'ErrorResponse':
        return cls(
            success=False,
            message=message,
            error_code=error_code,
            error_details=error_details,
            errors={"status_code": status_code}
        )


class SuccessResponse(APIResponse):
    """Success response format"""

    @classmethod
    def create(
        cls,
        data: Any = None,
        message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> 'SuccessResponse':
        return cls(
            success=True,
            data=data,
            message=message,
            meta=meta
        )


# Convenience functions for common responses
def success_response(data: Any = None, message: str = "Operation successful") -> SuccessResponse:
    """Create a success response"""
    return SuccessResponse.create(data=data, message=message)


def error_response(
    error_code: str,
    message: str,
    error_details: Optional[Dict[str, Any]] = None,
    status_code: int = 400
) -> ErrorResponse:
    """Create an error response"""
    return ErrorResponse.create(
        error_code=error_code,
        message=message,
        error_details=error_details,
        status_code=status_code
    )


def paginated_response(
    data: List[Any],
    page: int = 1,
    limit: int = 20,
    total: int = 0,
    message: str = "Data retrieved successfully"
) -> PaginatedResponse:
    """Create a paginated response"""
    return PaginatedResponse.create(
        data=data,
        page=page,
        limit=limit,
        total=total,
        message=message
    )


# Common error codes
class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"