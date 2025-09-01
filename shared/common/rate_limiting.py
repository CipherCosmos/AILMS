"""
Enhanced rate limiting system for LMS microservices
"""
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from shared.common.cache import cache_manager
from shared.common.logging import get_logger
from shared.common.errors import RateLimitError

logger = get_logger("common-rate-limiting")


class RateLimitRule:
    """Rate limit rule definition"""

    def __init__(
        self,
        requests: int,
        window_seconds: int,
        burst_limit: Optional[int] = None,
        strategy: str = "fixed_window"
    ):
        self.requests = requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or requests * 2
        self.strategy = strategy  # fixed_window, sliding_window, token_bucket


class RateLimiter:
    """Advanced rate limiter with multiple strategies"""

    def __init__(self):
        self.rules: Dict[str, RateLimitRule] = {}
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.token_buckets: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def add_rule(self, endpoint: str, rule: RateLimitRule):
        """Add a rate limit rule for an endpoint"""
        self.rules[endpoint] = rule
        logger.info(f"Added rate limit rule for {endpoint}: {rule.requests} req/{rule.window_seconds}s")

    def get_rule(self, endpoint: str) -> Optional[RateLimitRule]:
        """Get rate limit rule for an endpoint"""
        return self.rules.get(endpoint)

    async def is_allowed(self, key: str, endpoint: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limits"""
        rule = self.get_rule(endpoint)
        if not rule:
            return True, {"allowed": True}

        if rule.strategy == "fixed_window":
            return await self._check_fixed_window(key, rule)
        elif rule.strategy == "sliding_window":
            return await self._check_sliding_window(key, rule)
        elif rule.strategy == "token_bucket":
            return await self._check_token_bucket(key, rule)
        else:
            return True, {"allowed": True}

    async def _check_fixed_window(self, key: str, rule: RateLimitRule) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window rate limiting"""
        cache_key = f"ratelimit:fixed:{key}:{int(time.time() / rule.window_seconds)}"

        # Get current count
        count = await cache_manager.get(cache_key)
        if count is None:
            count = 0

        count = int(count) if isinstance(count, str) else count
        count += 1

        # Check limit
        if count > rule.requests:
            remaining_time = rule.window_seconds - (int(time.time()) % rule.window_seconds)
            return False, {
                "allowed": False,
                "limit": rule.requests,
                "remaining": 0,
                "reset_in": remaining_time,
                "retry_after": remaining_time
            }

        # Update count
        await cache_manager.set(cache_key, count, ttl=rule.window_seconds)

        remaining = max(0, rule.requests - count)
        return True, {
            "allowed": True,
            "limit": rule.requests,
            "remaining": remaining,
            "reset_in": rule.window_seconds - (int(time.time()) % rule.window_seconds)
        }

    async def _check_sliding_window(self, key: str, rule: RateLimitRule) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window rate limiting"""
        now = time.time()
        window_start = now - rule.window_seconds

        # Clean old requests
        history = self.request_history[key]
        while history and history[0] < window_start:
            history.popleft()

        # Check if under limit
        if len(history) >= rule.requests:
            # Calculate reset time
            if history:
                reset_time = history[0] + rule.window_seconds
                retry_after = max(0, reset_time - now)
            else:
                retry_after = rule.window_seconds

            return False, {
                "allowed": False,
                "limit": rule.requests,
                "remaining": 0,
                "reset_in": int(retry_after),
                "retry_after": int(retry_after)
            }

        # Add current request
        history.append(now)

        remaining = rule.requests - len(history)
        return True, {
            "allowed": True,
            "limit": rule.requests,
            "remaining": remaining,
            "reset_in": rule.window_seconds
        }

    async def _check_token_bucket(self, key: str, rule: RateLimitRule) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket rate limiting"""
        if key not in self.token_buckets:
            self.token_buckets[key] = {
                "tokens": rule.burst_limit,
                "last_refill": time.time()
            }

        bucket = self.token_buckets[key]
        now = time.time()

        # Refill tokens
        time_passed = now - bucket["last_refill"]
        tokens_to_add = time_passed * (rule.requests / rule.window_seconds)
        bucket["tokens"] = min(rule.burst_limit, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now

        # Check if we have tokens
        if bucket["tokens"] < 1:
            # Calculate time to next token
            time_to_next = (1 - bucket["tokens"]) / (rule.requests / rule.window_seconds)
            return False, {
                "allowed": False,
                "limit": rule.requests,
                "remaining": 0,
                "reset_in": int(time_to_next),
                "retry_after": int(time_to_next)
            }

        # Consume token
        bucket["tokens"] -= 1

        return True, {
            "allowed": True,
            "limit": rule.requests,
            "remaining": int(bucket["tokens"]),
            "reset_in": rule.window_seconds
        }

    async def get_remaining_requests(self, key: str, endpoint: str) -> Dict[str, Any]:
        """Get remaining requests for a key and endpoint"""
        allowed, info = await self.is_allowed(key, endpoint)
        return info

    async def reset_limit(self, key: str, endpoint: str):
        """Reset rate limit for a key and endpoint"""
        rule = self.get_rule(endpoint)
        if not rule:
            return

        # Clear from cache
        cache_key = f"ratelimit:fixed:{key}:*"
        await cache_manager.invalidate_pattern(cache_key)

        # Clear from local storage
        if key in self.request_history:
            self.request_history[key].clear()

        if key in self.token_buckets:
            del self.token_buckets[key]

        logger.info(f"Reset rate limit for {key} on {endpoint}")

    def start_cleanup_task(self):
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_data())

    async def _cleanup_old_data(self):
        """Clean up old rate limiting data"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean every 5 minutes

                now = time.time()

                # Clean old request history
                for key, history in list(self.request_history.items()):
                    window_start = now - 3600  # Keep 1 hour of history
                    while history and history[0] < window_start:
                        history.popleft()

                    if not history:
                        del self.request_history[key]

                # Clean old token buckets
                for key, bucket in list(self.token_buckets.items()):
                    if now - bucket["last_refill"] > 3600:  # 1 hour
                        del self.token_buckets[key]

            except Exception as e:
                logger.error("Error in rate limit cleanup", extra={"error": str(e)})

    def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None


# Global rate limiter instance
rate_limiter = RateLimiter()

# Default rate limit rules
DEFAULT_RULES = {
    # API endpoints
    "/api/auth/login": RateLimitRule(requests=5, window_seconds=300),  # 5 per 5 minutes
    "/api/auth/register": RateLimitRule(requests=3, window_seconds=3600),  # 3 per hour
    "/api/auth/refresh": RateLimitRule(requests=10, window_seconds=3600),  # 10 per hour

    # Course operations
    "/api/courses": RateLimitRule(requests=100, window_seconds=3600),  # 100 per hour
    "/api/courses/ai/generate": RateLimitRule(requests=10, window_seconds=3600),  # 10 per hour

    # User operations
    "/api/users": RateLimitRule(requests=200, window_seconds=3600),  # 200 per hour

    # File operations
    "/api/files/upload": RateLimitRule(requests=50, window_seconds=3600),  # 50 per hour

    # AI operations (expensive)
    "/api/ai/generate": RateLimitRule(requests=20, window_seconds=3600),  # 20 per hour
    "/api/ai/analyze": RateLimitRule(requests=30, window_seconds=3600),  # 30 per hour
}

# Initialize default rules
for endpoint, rule in DEFAULT_RULES.items():
    rate_limiter.add_rule(endpoint, rule)


def get_client_key(request: Request) -> str:
    """Generate a unique key for rate limiting based on client"""
    # Use IP address as primary key
    client_ip = request.client.host if request.client else "unknown"

    # For authenticated requests, use user ID
    user_id = getattr(request.state, 'user_id', None) if hasattr(request, 'state') else None

    if user_id:
        return f"user:{user_id}"
    else:
        return f"ip:{client_ip}"


async def check_rate_limit(request: Request, endpoint: Optional[str] = None) -> Dict[str, Any]:
    """Check rate limit for a request"""
    if not endpoint:
        endpoint = request.url.path

    client_key = get_client_key(request)

    allowed, info = await rate_limiter.is_allowed(client_key, endpoint)

    if not allowed:
        raise RateLimitError(
            limit=info["limit"],
            window=info["reset_in"]
        )

    return info


def rate_limit_middleware(endpoint: Optional[str] = None, requests: int = 100, window_seconds: int = 3600):
    """Middleware decorator for rate limiting"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request from kwargs or args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break

            if request:
                # Use endpoint from decorator or request path
                check_endpoint = endpoint or request.url.path
                await check_rate_limit(request, check_endpoint)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# User type based rate limiting
USER_RATE_LIMITS = {
    "student": {
        "/api/courses/ai/generate": RateLimitRule(requests=5, window_seconds=3600),  # 5 per hour
        "/api/ai/analyze": RateLimitRule(requests=10, window_seconds=3600),  # 10 per hour
    },
    "instructor": {
        "/api/courses/ai/generate": RateLimitRule(requests=20, window_seconds=3600),  # 20 per hour
        "/api/ai/analyze": RateLimitRule(requests=50, window_seconds=3600),  # 50 per hour
    },
    "admin": {
        "/api/courses/ai/generate": RateLimitRule(requests=100, window_seconds=3600),  # 100 per hour
        "/api/ai/analyze": RateLimitRule(requests=200, window_seconds=3600),  # 200 per hour
    }
}


def apply_user_rate_limits(user_role: str):
    """Apply rate limits based on user role"""
    if user_role in USER_RATE_LIMITS:
        for endpoint, rule in USER_RATE_LIMITS[user_role].items():
            rate_limiter.add_rule(endpoint, rule)


# Burst handling
BURST_RULES = {
    "/api/auth/login": RateLimitRule(requests=3, window_seconds=60, burst_limit=5),  # Burst of 5, normal 3/min
    "/api/courses": RateLimitRule(requests=50, window_seconds=3600, burst_limit=100),  # Burst of 100, normal 50/hour
}


def apply_burst_limits():
    """Apply burst rate limits"""
    for endpoint, rule in BURST_RULES.items():
        rate_limiter.add_rule(endpoint, rule)


# Initialize burst limits
apply_burst_limits()


# Rate limit monitoring
async def get_rate_limit_stats() -> Dict[str, Any]:
    """Get rate limiting statistics"""
    return {
        "rules_count": len(rate_limiter.rules),
        "active_keys": len(rate_limiter.request_history) + len(rate_limiter.token_buckets),
        "rules": list(rate_limiter.rules.keys()),
        "history_size": sum(len(history) for history in rate_limiter.request_history.values()),
        "token_buckets_count": len(rate_limiter.token_buckets)
    }


# Rate limit headers
def add_rate_limit_headers(response, rate_limit_info: Dict[str, Any]):
    """Add rate limit headers to response"""
    if rate_limit_info.get("allowed"):
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + rate_limit_info.get("reset_in", 0))
    else:
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + rate_limit_info.get("retry_after", 0))
        response.headers["Retry-After"] = str(rate_limit_info.get("retry_after", 0))


# Start cleanup task
rate_limiter.start_cleanup_task()