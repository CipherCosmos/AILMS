"""
Advanced caching system for LMS microservices
"""
import asyncio
import json
import time
from typing import Any, Dict, Optional, Union, Callable
from contextlib import asynccontextmanager
try:
    import redis.asyncio as redis
except ImportError:
    import redis
from shared.config.config import settings
from shared.common.logging import get_logger

logger = get_logger("common-cache")

# Redis availability check
REDIS_AVAILABLE = False
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import redis
        REDIS_AVAILABLE = True
    except ImportError:
        pass


class RedisManager:
    """Redis connection manager with connection pooling"""

    def __init__(self):
        self.client: Optional[Any] = None
        self._connection_lock = asyncio.Lock()
        self.redis_available = REDIS_AVAILABLE

    async def connect(self) -> Any:
        """Connect to Redis with connection pooling"""
        if not self.redis_available:
            return None

        async with self._connection_lock:
            if self.client is not None:
                return self.client

            try:
                if REDIS_AVAILABLE:
                    # Parse Redis URL
                    redis_url = settings.redis_url
                    if "://" in redis_url:
                        # Handle redis://host:port format
                        parts = redis_url.replace("redis://", "").split(":")
                        host = parts[0] if len(parts) > 0 else "redis"
                        port = int(parts[1]) if len(parts) > 1 else 6379
                    else:
                        host = "redis"
                        port = 6379

                    self.client = redis.Redis(
                        host=host,
                        port=port,
                        db=0,
                        decode_responses=True,
                        max_connections=20,
                        retry_on_timeout=True,
                        socket_timeout=5,
                        socket_connect_timeout=5,
                        health_check_interval=30
                    )

                    # Test connection
                    if self.client:
                        await self.client.ping()

                    logger.info("Redis connection established", extra={
                        "host": host,
                        "port": port
                    })

                    return self.client

            except Exception as e:
                logger.error("Redis connection failed", extra={"error": str(e)})
                self.redis_available = False
                return None

    async def disconnect(self):
        """Close Redis connection"""
        async with self._connection_lock:
            if self.client:
                await self.client.close()
                self.client = None
                logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        try:
            client = await self.connect()
            return await client.get(key)
        except Exception as e:
            logger.warning("Redis get failed", extra={"key": key, "error": str(e)})
            return None

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in Redis with TTL"""
        try:
            client = await self.connect()
            return await client.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning("Redis set failed", extra={"key": key, "error": str(e)})
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            client = await self.connect()
            return await client.delete(key) > 0
        except Exception as e:
            logger.warning("Redis delete failed", extra={"key": key, "error": str(e)})
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            client = await self.connect()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning("Redis exists failed", extra={"key": key, "error": str(e)})
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key"""
        try:
            client = await self.connect()
            return await client.expire(key, ttl)
        except Exception as e:
            logger.warning("Redis expire failed", extra={"key": key, "error": str(e)})
            return False

    async def incr(self, key: str) -> int:
        """Increment value"""
        try:
            client = await self.connect()
            return await client.incr(key)
        except Exception as e:
            logger.warning("Redis incr failed", extra={"key": key, "error": str(e)})
            return 0


class LocalCache:
    """Local in-memory cache for frequently accessed data"""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from local cache"""
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry["expires"] > time.time():
                    return entry["value"]
                else:
                    # Remove expired entry
                    del self.cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in local cache"""
        async with self._lock:
            # Remove expired entries if cache is full
            if len(self.cache) >= self.max_size:
                await self._cleanup_expired()

            if len(self.cache) >= self.max_size:
                # Remove oldest entry (simple LRU)
                oldest_key = min(self.cache.keys(),
                               key=lambda k: self.cache[k]["expires"])
                del self.cache[oldest_key]

            self.cache[key] = {
                "value": value,
                "expires": time.time() + ttl
            }
            return True

    async def delete(self, key: str) -> bool:
        """Delete key from local cache"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()

    async def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry["expires"] <= current_time
        ]
        for key in expired_keys:
            del self.cache[key]


class CacheManager:
    """Advanced multi-level cache manager"""

    def __init__(self):
        self.redis = RedisManager()
        self.local_cache = LocalCache(max_size=500)
        self.cache_hits = 0
        self.cache_misses = 0
        self._stats_lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (local first, then Redis)"""
        # Try local cache first
        value = await self.local_cache.get(key)
        if value is not None:
            async with self._stats_lock:
                self.cache_hits += 1
            return value

        # Try Redis
        redis_value = await self.redis.get(key)
        if redis_value is not None:
            # Store in local cache for faster future access
            try:
                parsed_value = json.loads(redis_value)
                await self.local_cache.set(key, parsed_value, ttl=60)  # 1 minute local TTL
                async with self._stats_lock:
                    self.cache_hits += 1
                return parsed_value
            except json.JSONDecodeError:
                async with self._stats_lock:
                    self.cache_hits += 1
                return redis_value

        async with self._stats_lock:
            self.cache_misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = 300, local_ttl: int = 60) -> bool:
        """Set value in both caches"""
        try:
            # Serialize value for Redis
            if isinstance(value, (dict, list)):
                redis_value = json.dumps(value)
            else:
                redis_value = str(value)

            # Set in Redis
            redis_success = await self.redis.set(key, redis_value, ttl)

            # Set in local cache
            local_success = await self.local_cache.set(key, value, local_ttl)

            return redis_success and local_success

        except Exception as e:
            logger.warning("Cache set failed", extra={"key": key, "error": str(e)})
            return False

    async def delete(self, key: str) -> bool:
        """Delete from both caches"""
        redis_success = await self.redis.delete(key)
        local_success = await self.local_cache.delete(key)
        return redis_success or local_success

    async def exists(self, key: str) -> bool:
        """Check if key exists in either cache"""
        return await self.local_cache.get(key) is not None or await self.redis.exists(key)

    async def get_or_set(
        self,
        key: str,
        getter_func: Callable[[], Any],
        ttl: int = 300,
        force_refresh: bool = False
    ) -> Any:
        """Get from cache or set if not exists"""
        if not force_refresh:
            cached_value = await self.get(key)
            if cached_value is not None:
                return cached_value

        # Get fresh data
        try:
            value = await getter_func()
            await self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error("Failed to get fresh data for cache", extra={"key": key, "error": str(e)})
            raise

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            client = await self.redis.connect()

            # Get all keys matching pattern
            keys = await client.keys(pattern)

            if keys:
                # Delete from Redis
                await client.delete(*keys)

                # Delete from local cache (we'll delete all since pattern matching is complex)
                await self.local_cache.clear()

                logger.info("Invalidated cache pattern", extra={
                    "pattern": pattern,
                    "keys_deleted": len(keys)
                })

                return len(keys)

            return 0

        except Exception as e:
            logger.warning("Failed to invalidate cache pattern", extra={
                "pattern": pattern,
                "error": str(e)
            })
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._stats_lock:
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
                "local_cache_size": len(self.local_cache.cache)
            }

    async def clear_all(self):
        """Clear all cache data"""
        await self.local_cache.clear()
        try:
            client = await self.redis.connect()
            await client.flushdb()
            logger.info("All cache cleared")
        except Exception as e:
            logger.warning("Failed to clear Redis cache", extra={"error": str(e)})

    async def warmup_cache(self, warmup_data: Dict[str, Any]):
        """Warm up cache with initial data"""
        for key, (value, ttl) in warmup_data.items():
            await self.set(key, value, ttl)

        logger.info("Cache warmup completed", extra={
            "keys_warmed": len(warmup_data)
        })


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions
async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache"""
    return await cache_manager.get(key)


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Set value in cache"""
    return await cache_manager.set(key, value, ttl)


async def cache_delete(key: str) -> bool:
    """Delete from cache"""
    return await cache_manager.delete(key)


async def cache_get_or_set(key: str, getter_func: Callable[[], Any], ttl: int = 300) -> Any:
    """Get from cache or set if not exists"""
    return await cache_manager.get_or_set(key, getter_func, ttl)


async def cache_invalidate_pattern(pattern: str) -> int:
    """Invalidate cache pattern"""
    return await cache_manager.invalidate_pattern(pattern)


async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return await cache_manager.get_stats()


async def clear_cache():
    """Clear all cache"""
    await cache_manager.clear_all()


async def close_connection():
    """Close cache connections"""
    try:
        await cache_manager.redis.disconnect()
    except:
        pass  # Ignore errors during shutdown


async def health_check() -> Dict[str, Any]:
    """Cache health check"""
    try:
        # Test Redis connection
        redis_client = await cache_manager.redis.connect()
        if redis_client:
            await redis_client.ping()
            redis_status = "healthy"
        else:
            redis_status = "unavailable"

        # Get cache stats
        stats = await cache_manager.get_stats()

        return {
            "status": "healthy" if redis_status == "healthy" else "degraded",
            "redis": redis_status,
            "cache_hits": stats.get("cache_hits", 0),
            "cache_misses": stats.get("cache_misses", 0),
            "hit_rate": stats.get("hit_rate", 0),
            "local_cache_size": stats.get("local_cache_size", 0)
        }

    except Exception as e:
        logger.error("Cache health check failed", extra={"error": str(e)})
        return {"status": "unhealthy", "error": str(e)}


# Placeholder classes and constants for compatibility
class Cache:
    """Placeholder Cache class"""
    @staticmethod
    async def get(key: str):
        return await cache_manager.get(key)

    @staticmethod
    async def set(key: str, value, ttl: int = 300):
        return await cache_manager.set(key, value, ttl)

    @staticmethod
    async def delete(key: str):
        return await cache_manager.delete(key)


class CacheKeys:
    """Placeholder CacheKeys class"""
    @staticmethod
    def api_response(path: str, params: str):
        return f"api:{path}:{params}"


class CacheTTL:
    """Placeholder CacheTTL class"""
    DEFAULT = 300
    SHORT = 60
    LONG = 3600


# Cache key generators
def generate_user_cache_key(user_id: str, resource: str = "") -> str:
    """Generate cache key for user-related data"""
    return f"user:{user_id}:{resource}" if resource else f"user:{user_id}"


def generate_course_cache_key(course_id: str, resource: str = "") -> str:
    """Generate cache key for course-related data"""
    return f"course:{course_id}:{resource}" if resource else f"course:{course_id}"


def generate_list_cache_key(resource: str, filters: Dict[str, Any], page: int = 1, limit: int = 20) -> str:
    """Generate cache key for list queries"""
    filter_str = "_".join([f"{k}:{v}" for k, v in sorted(filters.items())])
    return f"{resource}:list:{filter_str}:page{page}:limit{limit}"


# Context manager for cache operations
@asynccontextmanager
async def cache_transaction():
    """Context manager for cache operations"""
    try:
        yield cache_manager
    except Exception as e:
        logger.error("Cache transaction failed", extra={"error": str(e)})
        raise
    finally:
        # Could add cleanup logic here if needed
        pass