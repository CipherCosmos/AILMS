"""
AI Service Authentication Middleware
"""
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from shared.common.logging import get_logger
from shared.common.errors import AuthenticationError, AuthorizationError
from ..utils.ai_utils import check_rate_limit, log_ai_metrics

logger = get_logger("ai-service-middleware")

class AIMiddleware(BaseHTTPMiddleware):
    """AI service specific middleware"""

    async def dispatch(self, request: Request, call_next):
        """Process request through middleware"""
        start_time = time.time()

        try:
            # Extract user information from request
            user_id = self._extract_user_id(request)

            # Check rate limits
            if user_id and not check_rate_limit(user_id, request.url.path.split('/')[-1]):
                raise HTTPException(429, "Rate limit exceeded")

            # Process request
            response = await call_next(request)

            # Log metrics
            if user_id:
                duration = time.time() - start_time
                log_ai_metrics(user_id, "request", 0, 0.0, duration)

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

class AIRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging AI requests"""

    async def dispatch(self, request: Request, call_next):
        """Log AI requests"""
        start_time = time.time()

        # Log request
        logger.info("AI request started", extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info("AI request completed", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_seconds": round(duration, 3),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return response

class AICostTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking AI usage costs"""

    async def dispatch(self, request: Request, call_next):
        """Track AI usage costs"""
        response = await call_next(request)

        # Extract cost information from response headers
        cost = response.headers.get("X-AI-Cost", "0.0")
        tokens = response.headers.get("X-AI-Tokens", "0")

        if cost != "0.0":
            logger.info("AI cost tracked", extra={
                "cost": float(cost),
                "tokens": int(tokens),
                "path": request.url.path,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        return response

class AIContentFilterMiddleware(BaseHTTPMiddleware):
    """Middleware for filtering AI content"""

    async def dispatch(self, request: Request, call_next):
        """Filter AI content for safety"""
        response = await call_next(request)

        # In production, this would check response content for safety
        # For now, just pass through
        return response

# Middleware classes - instantiated by FastAPI
# Usage in main.py:
# app.add_middleware(AIMiddleware)
# app.add_middleware(AIRequestLoggingMiddleware)
# app.add_middleware(AICostTrackingMiddleware)
# app.add_middleware(AIContentFilterMiddleware)