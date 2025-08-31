"""
Rate limiting implementation for API protection.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from starlette.responses import JSONResponse
from performance_config import performance_settings
import time
from typing import Dict, Any

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{performance_settings.rate_limit_requests} per {performance_settings.rate_limit_window_seconds} seconds"]
)

# Custom rate limit exceeded handler
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.retry_after,
            "limit": exc.limit,
            "remaining": exc.remaining,
            "reset_time": exc.reset_time
        },
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(exc.limit),
            "X-RateLimit-Remaining": str(exc.remaining),
            "X-RateLimit-Reset": str(exc.reset_time)
        }
    )

# Rate limit storage (in-memory for development, Redis for production)
class RateLimitStorage:
    """Simple in-memory rate limit storage."""

    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Dict[str, Any]:
        """Get rate limit data for key."""
        return self._storage.get(key, {
            "count": 0,
            "reset_time": time.time() + performance_settings.rate_limit_window_seconds
        })

    def set(self, key: str, data: Dict[str, Any]):
        """Set rate limit data for key."""
        self._storage[key] = data

    def increment(self, key: str) -> Dict[str, Any]:
        """Increment rate limit counter for key."""
        current = self.get(key)

        if time.time() > current["reset_time"]:
            # Reset window
            current = {
                "count": 1,
                "reset_time": time.time() + performance_settings.rate_limit_window_seconds
            }
        else:
            current["count"] += 1

        self.set(key, current)
        return current

# Global rate limit storage
rate_limit_storage = RateLimitStorage()

async def check_rate_limit(request: Request) -> bool:
    """Check if request should be rate limited."""
    if not performance_settings.rate_limit_enabled:
        return True

    client_ip = get_remote_address(request)
    rate_data = rate_limit_storage.increment(client_ip)

    if rate_data["count"] > performance_settings.rate_limit_requests:
        return False

    return True

# Rate limit decorators for specific endpoints
def auth_rate_limit():
    """Rate limit for authentication endpoints."""
    return limiter.limit("5 per minute")

def api_rate_limit():
    """Rate limit for general API endpoints."""
    return limiter.limit(f"{performance_settings.rate_limit_requests} per {performance_settings.rate_limit_window_seconds} seconds")

def heavy_operation_rate_limit():
    """Rate limit for heavy operations (AI generation, etc.)."""
    return limiter.limit("10 per hour")

# Middleware for rate limiting
def create_rate_limit_middleware():
    """Create rate limiting middleware."""
    return SlowAPIMiddleware(
        limiter=limiter,
        error_handler=rate_limit_exceeded_handler
    )

# Rate limit monitoring
class RateLimitMonitor:
    """Monitor rate limiting activity."""

    def __init__(self):
        self._stats: Dict[str, Dict[str, Any]] = {}

    def record_request(self, client_ip: str, endpoint: str, allowed: bool):
        """Record rate limit check."""
        key = f"{client_ip}:{endpoint}"
        if key not in self._stats:
            self._stats[key] = {
                "total_requests": 0,
                "blocked_requests": 0,
                "last_request": time.time()
            }

        self._stats[key]["total_requests"] += 1
        if not allowed:
            self._stats[key]["blocked_requests"] += 1
        self._stats[key]["last_request"] = time.time()

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get rate limiting statistics."""
        return self._stats.copy()

    def get_blocked_ips(self) -> list:
        """Get list of IPs that have been rate limited."""
        blocked = []
        for key, stats in self._stats.items():
            if stats["blocked_requests"] > 0:
                ip = key.split(":")[0]
                blocked.append({
                    "ip": ip,
                    "total_requests": stats["total_requests"],
                    "blocked_requests": stats["blocked_requests"],
                    "block_rate": stats["blocked_requests"] / stats["total_requests"]
                })
        return blocked

# Global monitor instance
rate_limit_monitor = RateLimitMonitor()