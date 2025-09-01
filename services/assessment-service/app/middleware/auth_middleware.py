"""
Assessment Service Authentication Middleware
"""
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from shared.common.logging import get_logger
from shared.common.errors import AuthenticationError, AuthorizationError
from ..utils.assessment_utils import check_assignment_access

logger = get_logger("assessment-service-middleware")

class AssessmentMiddleware(BaseHTTPMiddleware):
    """Assessment service specific middleware"""

    async def dispatch(self, request: Request, call_next):
        """Process request through middleware"""
        start_time = time.time()

        try:
            # Extract user information from request
            user_id = self._extract_user_id(request)
            user_role = self._extract_user_role(request)

            # Check rate limits based on user role
            if user_id:
                await self._check_rate_limits(user_id, user_role, request.url.path)

            # Process request
            response = await call_next(request)

            # Log metrics
            if user_id:
                duration = time.time() - start_time
                logger.info("Assessment request completed", extra={
                    "user_id": user_id,
                    "user_role": user_role,
                    "path": request.url.path,
                    "method": request.method,
                    "duration_seconds": round(duration, 3)
                })

            return response

        except (AuthenticationError, AuthorizationError) as e:
            logger.warning("Authentication/Authorization error", extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e)
            })
            raise HTTPException(401 if isinstance(e, AuthenticationError) else 403, str(e))
        except Exception as e:
            logger.error("Middleware error", extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e)
            })
            raise HTTPException(500, "Internal server error")

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request headers"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        try:
            # Extract token from Bearer header
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                # In production, this would decode and validate the JWT
                # For now, return a mock user ID
                return "user_123"
        except Exception as e:
            logger.warning("Failed to extract user ID", extra={"error": str(e)})

        return None

    def _extract_user_role(self, request: Request) -> str:
        """Extract user role from request headers"""
        role_header = request.headers.get("X-User-Role")
        return role_header or "student"

    async def _check_rate_limits(self, user_id: str, user_role: str, path: str) -> None:
        """Check rate limits based on user role and endpoint"""
        # Different rate limits for different user roles and endpoints
        from ..config.config import assessment_service_settings

        if "assignment" in path and "create" in path:
            if user_role == "instructor":
                limit = assessment_service_settings.assignment_creation_rate_limit
            else:
                limit = 5  # Students can't create assignments
        elif "submission" in path:
            if user_role == "student":
                limit = assessment_service_settings.submission_rate_limit
            else:
                limit = 20  # Instructors can view many submissions
        elif "grade" in path:
            if user_role == "instructor":
                limit = assessment_service_settings.grading_rate_limit
            else:
                limit = 10  # Students can check grades
        else:
            limit = 30  # Default limit

        # This would integrate with Redis for actual rate limiting
        logger.info("Rate limit check", extra={
            "user_id": user_id,
            "user_role": user_role,
            "path": path,
            "limit": limit
        })

class AssessmentRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging assessment requests"""

    async def dispatch(self, request: Request, call_next):
        """Log assessment requests"""
        start_time = time.time()

        # Log request
        logger.info("Assessment request started", extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "user_agent": request.headers.get("User-Agent", ""),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info("Assessment request completed", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_seconds": round(duration, 3),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return response

class AssessmentContentValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating assessment content"""

    async def dispatch(self, request: Request, call_next):
        """Validate assessment content"""
        # Check content length for submissions and assignments
        if request.method in ["POST", "PUT"]:
            content_length = request.headers.get("Content-Length")
            if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(413, "Content too large")

        response = await call_next(request)
        return response

class AssessmentSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for assessment security checks"""

    async def dispatch(self, request: Request, call_next):
        """Perform security checks"""
        # Check for suspicious patterns
        suspicious_patterns = ["<script", "javascript:", "eval(", "document.cookie"]

        # This would check request body for malicious content
        # For now, just pass through
        response = await call_next(request)
        return response

# Middleware classes - instantiated by FastAPI
# Usage in main.py:
# app.add_middleware(AssessmentMiddleware)
# app.add_middleware(AssessmentRequestLoggingMiddleware)
# app.add_middleware(AssessmentContentValidationMiddleware)
# app.add_middleware(AssessmentSecurityMiddleware)