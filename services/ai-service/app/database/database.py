"""
AI Service Database Operations
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import DatabaseError, NotFoundError
from config.config import ai_service_settings

# Simple cache implementation for now
class SimpleCache:
    """Simple in-memory cache for AI service"""
    def __init__(self):
        self.cache = {}

    async def init_cache(self):
        pass

    async def close(self):
        self.cache.clear()

    async def get(self, key: str) -> Optional[str]:
        return self.cache.get(key)

    async def set(self, key: str, value: str, ttl: int = 300):
        self.cache[key] = value
        # In production, implement TTL logic

    async def delete(self, key: str):
        self.cache.pop(key, None)

logger = get_logger("ai-service-db")

class AIDatabase:
    """AI service database operations with caching"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.cache = SimpleCache()
        self._initialized = False

    async def init_db(self):
        """Initialize database connection"""
        if self._initialized:
            return

        try:
            self.client = AsyncIOMotorClient(settings.mongo_url)
            self.db = self.client[settings.db_name]
            await self._create_indexes()
            await self.cache.init_cache()
            self._initialized = True
            logger.info("AI database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize AI database", extra={"error": str(e)})
            raise DatabaseError("init_db", f"Database initialization failed: {str(e)}")

    async def close_db(self):
        """Close database connection"""
        if self.client:
            self.client.close()
        await self.cache.close()
        self._initialized = False
        logger.info("AI database connection closed")

    async def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # AI Requests indexes
            await self.db.ai_requests.create_index("user_id")
            await self.db.ai_requests.create_index("request_type")
            await self.db.ai_requests.create_index("created_at")
            await self.db.ai_requests.create_index([("user_id", 1), ("created_at", -1)])

            # AI Results indexes
            await self.db.ai_results.create_index("request_id")
            await self.db.ai_results.create_index("user_id")
            await self.db.ai_results.create_index("result_type")
            await self.db.ai_results.create_index("created_at")

            # User Preferences indexes
            await self.db.user_ai_preferences.create_index("user_id", unique=True)
            await self.db.user_ai_preferences.create_index("updated_at")

            # Content Cache indexes
            await self.db.ai_content_cache.create_index("content_hash", unique=True)
            await self.db.ai_content_cache.create_index("created_at")

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error("Failed to create database indexes", extra={"error": str(e)})

    # AI Request operations
    async def log_ai_request(self, request_data: Dict[str, Any]) -> str:
        """Log AI request"""
        try:
            request_data["created_at"] = datetime.now(timezone.utc)
            result = await self.db.ai_requests.insert_one(request_data)
            request_id = str(result.inserted_id)

            logger.info("AI request logged", extra={"request_id": request_id})
            return request_id

        except Exception as e:
            logger.error("Failed to log AI request", extra={"error": str(e)})
            raise DatabaseError("log_ai_request", f"AI request logging failed: {str(e)}")

    async def get_user_requests(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's AI requests"""
        try:
            requests = await self.db.ai_requests.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(limit).to_list(limit)
            return requests

        except Exception as e:
            logger.error("Failed to get user requests", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_user_requests", f"User requests retrieval failed: {str(e)}")

    # AI Results operations
    async def save_ai_result(self, result_data: Dict[str, Any]) -> str:
        """Save AI result"""
        try:
            result_data["created_at"] = datetime.now(timezone.utc)
            result = await self.db.ai_results.insert_one(result_data)
            result_id = str(result.inserted_id)

            logger.info("AI result saved", extra={"result_id": result_id})
            return result_id

        except Exception as e:
            logger.error("Failed to save AI result", extra={"error": str(e)})
            raise DatabaseError("save_ai_result", f"AI result saving failed: {str(e)}")

    async def get_ai_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Get AI result"""
        try:
            result = await self.db.ai_results.find_one({"_id": result_id})
            return result

        except Exception as e:
            logger.error("Failed to get AI result", extra={
                "result_id": result_id,
                "error": str(e)
            })
            raise DatabaseError("get_ai_result", f"AI result retrieval failed: {str(e)}")

    # User Preferences operations
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user AI preferences"""
        try:
            preferences = await self.db.user_ai_preferences.find_one({"user_id": user_id})
            return preferences

        except Exception as e:
            logger.error("Failed to get user preferences", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_user_preferences", f"User preferences retrieval failed: {str(e)}")

    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user AI preferences"""
        try:
            preferences["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.user_ai_preferences.update_one(
                {"user_id": user_id},
                {"$set": preferences},
                upsert=True
            )

            return result.modified_count > 0 or result.upserted_id is not None

        except Exception as e:
            logger.error("Failed to update user preferences", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_user_preferences", f"User preferences update failed: {str(e)}")

    # Content Cache operations
    async def get_cached_content(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached content"""
        try:
            cached = await self.db.ai_content_cache.find_one({"content_hash": content_hash})
            return cached

        except Exception as e:
            logger.error("Failed to get cached content", extra={
                "content_hash": content_hash,
                "error": str(e)
            })
            raise DatabaseError("get_cached_content", f"Cached content retrieval failed: {str(e)}")

    async def save_cached_content(self, content_data: Dict[str, Any]) -> str:
        """Save cached content"""
        try:
            content_data["created_at"] = datetime.now(timezone.utc)
            result = await self.db.ai_content_cache.insert_one(content_data)
            cache_id = str(result.inserted_id)

            logger.info("Content cached", extra={"cache_id": cache_id})
            return cache_id

        except Exception as e:
            logger.error("Failed to save cached content", extra={"error": str(e)})
            raise DatabaseError("save_cached_content", f"Cached content saving failed: {str(e)}")

    # Analytics operations
    async def get_usage_stats(self, user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get AI usage statistics"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Build query
            query: Dict[str, Any] = {"created_at": {"$gte": start_date}}
            if user_id:
                query["user_id"] = user_id

            # Get request counts by type
            pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": "$request_type",
                    "count": {"$sum": 1},
                    "total_tokens": {"$sum": "$tokens_used"}
                }}
            ]

            stats_result = await self.db.ai_requests.aggregate(pipeline).to_list(10)

            # Get total requests
            total_requests = await self.db.ai_requests.count_documents(query)

            return {
                "total_requests": total_requests,
                "requests_by_type": {item["_id"]: item["count"] for item in stats_result},
                "total_tokens_used": sum(item.get("total_tokens", 0) for item in stats_result),
                "period_days": days
            }

        except Exception as e:
            logger.error("Failed to get usage stats", extra={"error": str(e)})
            raise DatabaseError("get_usage_stats", f"Usage stats retrieval failed: {str(e)}")

# Global database instance
ai_db = AIDatabase()