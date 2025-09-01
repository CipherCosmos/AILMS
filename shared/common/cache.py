"""
Redis caching utilities for LMS microservices
"""
import json
import pickle
from typing import Any, Optional, Union, Dict
from datetime import timedelta
import redis.asyncio as redis
from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import ExternalServiceError

logger = get_logger("common-cache")

class CacheManager:
    """Redis cache manager with error handling and serialization"""

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> redis.Redis:
        """Connect to Redis with error handling"""
        async with self._connection_lock:
            if self.client is not None:
                return self.client

            try:
                self.client = redis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,  # Decode responses to strings
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    health_check_interval=30
                )

                # Test connection
                await self.client.ping()

                logger.info("Redis connection established", extra={
                    "redis_url": settings.redis_url.replace("://", "://***:***@")  # Mask credentials in logs
                })

                return self.client

            except redis.ConnectionError as e:
                logger.error("Redis connection failed", extra={"error": str(e)})
                raise ExternalServiceError("redis", "connection", str(e))
            except Exception as e:
                logger.error("Redis initialization error", extra={"error": str(e)})
                raise ExternalServiceError("redis", "initialization", str(e))

    async def disconnect(self):
        """Close Redis connection"""
        async with self._connection_lock:
            if self.client:
                await self.client.close()
                self.client = None
                logger.info("Redis connection closed")

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            if not self.client:
                return {"status": "disconnected"}

            # Test connection
            await self.client.ping()

            # Get basic info
            info = await self.client.info()

            return {
                "status": "healthy",
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "total_connections_received": info.get("total_connections_received")
            }

        except Exception as e:
            logger.error("Redis health check failed", extra={"error": str(e)})
            return {"status": "unhealthy", "error": str(e)}

# Global cache manager instance
cache_manager = CacheManager()

async def get_cache_client() -> redis.Redis:
    """Get Redis client with automatic connection management"""
    return await cache_manager.connect()

class Cache:
    """High-level cache operations"""

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = await get_cache_client()
            value = await client.get(key)
            if value:
                logger.debug("Cache hit", extra={"key": key})
                return json.loads(value)
            logger.debug("Cache miss", extra={"key": key})
            return None
        except Exception as e:
            logger.error("Cache get error", extra={"key": key, "error": str(e)})
            return None

    @staticmethod
    async def set(key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            client = await get_cache_client()
            json_value = json.dumps(value, default=str)

            if ttl_seconds:
                await client.setex(key, ttl_seconds, json_value)
            else:
                await client.set(key, json_value)

            logger.debug("Cache set", extra={"key": key, "ttl": ttl_seconds})
            return True
        except Exception as e:
            logger.error("Cache set error", extra={"key": key, "error": str(e)})
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        """Delete value from cache"""
        try:
            client = await get_cache_client()
            result = await client.delete(key)
            logger.debug("Cache delete", extra={"key": key, "deleted": result > 0})
            return result > 0
        except Exception as e:
            logger.error("Cache delete error", extra={"key": key, "error": str(e)})
            return False

    @staticmethod
    async def exists(key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await get_cache_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error("Cache exists error", extra={"key": key, "error": str(e)})
            return False

    @staticmethod
    async def expire(key: str, ttl_seconds: int) -> bool:
        """Set expiration time for key"""
        try:
            client = await get_cache_client()
            return await client.expire(key, ttl_seconds)
        except Exception as e:
            logger.error("Cache expire error", extra={"key": key, "error": str(e)})
            return False

    @staticmethod
    async def get_or_set(key: str, default_func, ttl_seconds: Optional[int] = None):
        """Get value from cache or set it using default function"""
        value = await Cache.get(key)
        if value is not None:
            return value

        # Cache miss - compute value
        value = await default_func()
        if value is not None:
            await Cache.set(key, value, ttl_seconds)

        return value

class CacheKeys:
    """Standardized cache key patterns"""

    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"user:profile:{user_id}"

    @staticmethod
    def course_details(course_id: str) -> str:
        return f"course:details:{course_id}"

    @staticmethod
    def course_progress(user_id: str, course_id: str) -> str:
        return f"course:progress:{user_id}:{course_id}"

    @staticmethod
    def user_permissions(user_id: str) -> str:
        return f"user:permissions:{user_id}"

    @staticmethod
    def api_response(endpoint: str, params: str) -> str:
        """Cache API responses"""
        return f"api:response:{endpoint}:{hash(params)}"

    @staticmethod
    def analytics_data(query_type: str, params: str) -> str:
        return f"analytics:{query_type}:{hash(params)}"

# Cache TTL constants
class CacheTTL:
    """Standard cache TTL values in seconds"""

    USER_PROFILE = 300      # 5 minutes
    COURSE_DETAILS = 600    # 10 minutes
    COURSE_PROGRESS = 180   # 3 minutes
    USER_PERMISSIONS = 300  # 5 minutes
    API_RESPONSE = 60       # 1 minute
    ANALYTICS_DATA = 1800   # 30 minutes
    SESSION_DATA = 3600     # 1 hour

async def health_check() -> Dict[str, Any]:
    """Cache health check"""
    return await cache_manager.health_check()

async def close_connection():
    """Close cache connection"""
    await cache_manager.disconnect()