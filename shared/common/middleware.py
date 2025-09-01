"""
Common middleware for LMS microservices
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.cache import Cache, CacheKeys, CacheTTL

logger = get_logger("common-middleware")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        start_time = time.time()

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None,
            },
            correlation_id=correlation_id
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "status_code": response.status_code,
                    "process_time": round(process_time, 3),
                    "response_size": response.headers.get("content-length"),
                },
                correlation_id=correlation_id
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time"] = str(round(process_time, 3))

            return response

        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "error": str(e),
                    "process_time": round(process_time, 3),
                },
                correlation_id=correlation_id
            )
            raise

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client identifier (IP address for now)
        client_ip = request.client.host if request.client else "unknown"

        # Create rate limit key
        rate_key = f"rate_limit:{client_ip}:{int(time.time() / 60)}"  # Per minute window

        try:
            # Check current request count
            current_count = await Cache.get(rate_key) or 0

            if current_count >= self.requests_per_minute:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_ip": client_ip,
                        "current_count": current_count,
                        "limit": self.requests_per_minute,
                    },
                    correlation_id=getattr(request.state, 'correlation_id', None)
                )

                response = Response(
                    content='{"error": "Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json"
                )
                response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["Retry-After"] = "60"
                return response

            # Increment counter
            await Cache.set(rate_key, current_count + 1, ttl_seconds=60)

            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(self.requests_per_minute - current_count - 1)

            return response

        except Exception as e:
            logger.error(
                "Rate limiting error",
                extra={"error": str(e), "client_ip": client_ip},
                correlation_id=getattr(request.state, 'correlation_id', None)
            )
            # If rate limiting fails, allow the request
            return await call_next(request)

class CacheMiddleware(BaseHTTPMiddleware):
    """Response caching middleware"""

    def __init__(self, app, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        # Create cache key
        cache_key = CacheKeys.api_response(request.url.path, str(request.query_params))

        try:
            # Try to get cached response
            cached_response = await Cache.get(cache_key)
            if cached_response:
                logger.debug("Serving from cache", extra={"cache_key": cache_key})
                return Response(
                    content=cached_response["content"],
                    status_code=cached_response["status_code"],
                    headers=cached_response["headers"]
                )

            # Process request
            response = await call_next(request)

            # Cache successful responses
            if response.status_code == 200:
                response_data = {
                    "content": response.body.decode() if hasattr(response, 'body') else "",
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                await Cache.set(cache_key, response_data, ttl_seconds=self.cache_ttl)

            return response

        except Exception as e:
            logger.error(
                "Cache middleware error",
                extra={"error": str(e), "cache_key": cache_key},
                correlation_id=getattr(request.state, 'correlation_id', None)
            )
            # If caching fails, continue without caching
            return await call_next(request)

def create_cors_middleware() -> CORSMiddleware:
    """Create CORS middleware with proper configuration"""
    return CORSMiddleware(
        allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
        max_age=86400,  # 24 hours
    )

def create_trusted_host_middleware() -> TrustedHostMiddleware:
    """Create trusted host middleware for production"""
    if settings.environment == "production":
        return TrustedHostMiddleware(
            allowed_hosts=["your-domain.com", "*.your-domain.com"]
        )
    return TrustedHostMiddleware(allowed_hosts=["*"])

# Common middleware stack
def get_common_middleware():
    """Get list of common middleware for services"""
    middleware = [
        create_cors_middleware(),
        RequestLoggingMiddleware,
    ]

    # Add rate limiting in production
    if settings.environment == "production":
        middleware.append(lambda app: RateLimitMiddleware(app, requests_per_minute=100))

    # Add trusted host middleware in production
    if settings.environment == "production":
        middleware.append(create_trusted_host_middleware())

    return middleware