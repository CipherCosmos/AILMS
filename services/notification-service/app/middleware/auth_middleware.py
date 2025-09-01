"""
Notification Service Authentication Middleware
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time

from shared.common.logging import get_logger

logger = get_logger("notification-service-middleware")

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for notification service"""

    def __init__(self, app, exclude_paths=None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Extract token from header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )

        token = auth_header.split(" ")[1]

        # Validate token (simplified - in production would validate with auth service)
        try:
            import jwt
            from shared.config.config import settings

            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

            # Add user info to request state
            request.state.user = {
                "id": payload.get("sub"),
                "role": payload.get("role", "student"),
                "email": payload.get("email", ""),
                "name": payload.get("name", "")
            }

        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired"}
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"}
            )
        except Exception as e:
            logger.error("Authentication error", extra={"error": str(e)})
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication failed"}
            )

        # Continue with request
        response = await call_next(request)
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        logger.info("Request started", extra={
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
            "user_agent": request.headers.get("User-Agent", "")
        })

        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        logger.info("Request completed", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": round(process_time, 4)
        })

        return response