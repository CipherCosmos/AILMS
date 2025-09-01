"""
Authentication middleware for auth service
"""
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from shared.common.logging import get_logger
from shared.common.monitoring import metrics_collector
from ..services.auth_service import AuthService
from ..database import auth_db

logger = get_logger("auth-middleware")


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and authorization"""

    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/register",
            "/auth/login"
        ]

    async def dispatch(self, request: Request, call_next):
        """Process each request"""

        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Extract token from header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            await metrics_collector.increment_counter("auth_failures", tags={"reason": "missing_token"})
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid authorization header"}
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            # Validate token and get user
            user = await AuthService.get_current_user(token)

            # Add user to request state
            request.state.user = user
            request.state.user_id = user.id
            request.state.user_role = user.role

            # Update session activity if applicable
            if hasattr(request.state, 'session_id'):
                await auth_db.update_session_activity(request.state.session_id)

            # Log successful authentication
            logger.info("Request authenticated", extra={
                "user_id": user.id,
                "path": request.url.path,
                "method": request.method
            })

            # Update metrics
            await metrics_collector.increment_counter("auth_success")

            # Continue with request
            response = await call_next(request)

            # Add user info to response headers for debugging
            if request.headers.get("X-Debug", "").lower() == "true":
                response.headers["X-User-ID"] = user.id
                response.headers["X-User-Role"] = user.role

            return response

        except Exception as e:
            # Log authentication failure
            logger.warning("Authentication failed", extra={
                "error": str(e),
                "path": request.url.path,
                "ip": request.client.host if request.client else None
            })

            # Update metrics
            await metrics_collector.increment_counter("auth_failures", tags={"reason": "invalid_token"})

            return JSONResponse(
                status_code=401,
                content={"error": "Authentication failed", "details": str(e)}
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Remove server header for security
        response.headers.pop("Server", None)

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for detailed request logging"""

    async def dispatch(self, request: Request, call_next):
        import time

        start_time = time.time()

        # Log request
        logger.info("Request started", extra={
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
            "user_agent": request.headers.get("User-Agent", ""),
            "ip": request.client.host if request.client else None
        })

        try:
            response = await call_next(request)

            # Calculate response time
            response_time = time.time() - start_time

            # Log response
            logger.info("Request completed", extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time": round(response_time * 1000, 2),  # ms
                "user_id": getattr(request.state, 'user_id', None)
            })

            # Update metrics
            await metrics_collector.histogram(
                "request_duration",
                response_time,
                tags={
                    "method": request.method,
                    "path": request.url.path,
                    "status": str(response.status_code)
                }
            )

            return response

        except Exception as e:
            # Log error
            response_time = time.time() - start_time
            logger.error("Request failed", extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "response_time": round(response_time * 1000, 2),
                "user_id": getattr(request.state, 'user_id', None)
            })

            # Update error metrics
            await metrics_collector.increment_counter("request_errors", tags={"path": request.url.path})

            raise