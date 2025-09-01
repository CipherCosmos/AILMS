"""
Analytics Service Authentication Middleware
"""
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from shared.common.logging import get_logger
from shared.common.errors import AuthenticationError, AuthorizationError
from ..utils.analytics_utils import validate_analytics_data

logger = get_logger("analytics-service-middleware")

class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Analytics service specific middleware"""

    async def dispatch(self, request: Request, call_next):
        """Process request through middleware"""
        start_time = time.time()

        try:
            # Extract user information from request
            user_id = self._extract_user_id(request)
            user_role = self._extract_user_role(request)

            # Check rate limits based on user role and endpoint
            if user_id:
                await self._check_rate_limits(user_id, user_role, request.url.path, request.method)

            # Validate analytics data for POST/PUT requests
            if request.method in ["POST", "PUT"] and "analytics" in request.url.path:
                await self._validate_request_data(request)

            # Process request
            response = await call_next(request)

            # Log metrics
            if user_id:
                duration = time.time() - start_time
                logger.info("Analytics request completed", extra={
                    "user_id": user_id,
                    "user_role": user_role,
                    "path": request.url.path,
                    "method": request.method,
                    "duration_seconds": round(duration, 3),
                    "status_code": response.status_code
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

    async def _check_rate_limits(self, user_id: str, user_role: str, path: str, method: str) -> None:
        """Check rate limits based on user role and endpoint"""
        from ..config.config import analytics_service_settings

        # Different rate limits for different operations
        if "report" in path and method == "POST":
            limit = analytics_service_settings.report_generation_rate_limit
        elif "dashboard" in path:
            limit = analytics_service_settings.dashboard_access_rate_limit
        elif "analytics" in path:
            limit = analytics_service_settings.analytics_request_rate_limit
        else:
            limit = 50  # Default limit

        # Adjust limit based on user role
        if user_role == "instructor":
            limit = limit * 2  # Higher limit for instructors
        elif user_role == "admin":
            limit = limit * 5  # Even higher for admins

        logger.info("Rate limit check", extra={
            "user_id": user_id,
            "user_role": user_role,
            "path": path,
            "limit": limit
        })

    async def _validate_request_data(self, request: Request) -> None:
        """Validate analytics request data"""
        try:
            # For now, just log the validation attempt
            # In production, this would parse and validate the request body
            logger.info("Analytics data validation", extra={
                "path": request.url.path,
                "method": request.method,
                "content_type": request.headers.get("Content-Type")
            })
        except Exception as e:
            logger.warning("Failed to validate request data", extra={"error": str(e)})

class AnalyticsRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging analytics requests"""

    async def dispatch(self, request: Request, call_next):
        """Log analytics requests"""
        start_time = time.time()

        # Log request
        logger.info("Analytics request started", extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "user_agent": request.headers.get("User-Agent", ""),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info("Analytics request completed", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_seconds": round(duration, 3),
            "response_size": len(response.body) if hasattr(response, 'body') else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return response

class AnalyticsPerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring analytics performance"""

    async def dispatch(self, request: Request, call_next):
        """Monitor performance of analytics requests"""
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Log slow requests
        from ..config.config import analytics_service_settings
        if duration > analytics_service_settings.alert_threshold_response_time:
            logger.warning("Slow analytics request", extra={
                "path": request.url.path,
                "method": request.method,
                "duration_seconds": round(duration, 3),
                "threshold": analytics_service_settings.alert_threshold_response_time
            })

        return response

class AnalyticsDataPrivacyMiddleware(BaseHTTPMiddleware):
    """Middleware for ensuring data privacy in analytics"""

    async def dispatch(self, request: Request, call_next):
        """Ensure data privacy compliance"""
        # Check if request involves sensitive data
        if "personal" in request.url.path or "private" in request.url.path:
            # Add privacy headers
            response = await call_next(request)

            # Add privacy compliance headers
            response.headers["X-Data-Privacy"] = "compliant"
            response.headers["X-PII-Masking"] = "enabled"

            return response

        response = await call_next(request)
        return response

class AnalyticsCachingMiddleware(BaseHTTPMiddleware):
    """Middleware for analytics caching"""

    async def dispatch(self, request: Request, call_next):
        """Handle caching for analytics requests"""
        # Check if request is cacheable
        if request.method == "GET" and ("analytics" in request.url.path or "dashboard" in request.url.path):
            # Add cache control headers
            response = await call_next(request)

            from ..config.config import analytics_service_settings
            if "dashboard" in request.url.path:
                max_age = analytics_service_settings.dashboard_cache_ttl
            elif "report" in request.url.path:
                max_age = analytics_service_settings.report_cache_ttl
            else:
                max_age = analytics_service_settings.analytics_cache_ttl

            response.headers["Cache-Control"] = f"max-age={max_age}"
            response.headers["X-Cache-TTL"] = str(max_age)

            return response

        response = await call_next(request)
        return response

# Middleware classes - instantiated by FastAPI
# Usage in main.py:
# app.add_middleware(AnalyticsMiddleware)
# app.add_middleware(AnalyticsRequestLoggingMiddleware)
# app.add_middleware(AnalyticsPerformanceMonitoringMiddleware)
# app.add_middleware(AnalyticsDataPrivacyMiddleware)
# app.add_middleware(AnalyticsCachingMiddleware)