"""
Redis-based caching layer for performance optimization.
"""
import json
import redis.asyncio as redis
from typing import Any, Optional, Dict, List
import asyncio
from functools import wraps
from performance_config import performance_settings

class CacheManager:
    """Redis cache manager for LMS backend."""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize Redis connection."""
        if not performance_settings.cache_enabled:
            return

        try:
            self.redis = redis.Redis.from_url(
                performance_settings.redis_url,
                decode_responses=True,
                max_connections=10
            )
            # Test connection
            await self.redis.ping()
            print("✅ Redis cache initialized successfully")
        except Exception as e:
            print(f"⚠️  Redis cache initialization failed: {e}")
            self.redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis:
            return None

        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self.redis:
            return False

        try:
            ttl = ttl or performance_settings.cache_ttl_seconds
            data = json.dumps(value, default=str)
            return await self.redis.set(key, data, ex=ttl)
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis:
            return False

        try:
            return await self.redis.delete(key) > 0
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.redis:
            return 0

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
        except Exception as e:
            print(f"Cache clear pattern error: {e}")
        return 0

    async def get_or_set(self, key: str, func, ttl: Optional[int] = None):
        """Get from cache or set if not exists."""
        # Try to get from cache first
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        # If not in cache, execute function
        value = await func()

        # Cache the result
        await self.set(key, value, ttl)
        return value

# Global cache instance
cache_manager = CacheManager()

def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not performance_settings.cache_enabled:
                return await func(*args, **kwargs)

            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend([str(arg) for arg in args[1:]])  # Skip 'self'
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)

            async def execute_func():
                return await func(*args, **kwargs)

            return await cache_manager.get_or_set(cache_key, execute_func, ttl)

        return wrapper
    return decorator

# Cache key generators
def course_cache_key(course_id: str, user_id: Optional[str] = None):
    """Generate cache key for course data."""
    if user_id:
        return f"course:{course_id}:user:{user_id}"
    return f"course:{course_id}"

def user_cache_key(user_id: str):
    """Generate cache key for user data."""
    return f"user:{user_id}"

def courses_list_cache_key(filters: Dict[str, Any]):
    """Generate cache key for courses list."""
    sorted_filters = sorted(filters.items())
    filter_str = ":".join([f"{k}:{v}" for k, v in sorted_filters])
    return f"courses:list:{filter_str}"

# Cache invalidation helpers
async def invalidate_course_cache(course_id: str):
    """Invalidate all cache entries for a course."""
    patterns = [
        f"course:{course_id}*",
        "courses:list*"
    ]
    for pattern in patterns:
        await cache_manager.clear_pattern(pattern)

async def invalidate_user_cache(user_id: str):
    """Invalidate all cache entries for a user."""
    patterns = [
        f"user:{user_id}*",
        f"course:*:user:{user_id}*"
    ]
    for pattern in patterns:
        await cache_manager.clear_pattern(pattern)