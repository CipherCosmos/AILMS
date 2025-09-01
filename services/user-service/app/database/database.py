"""
User Service Database Operations
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import DatabaseError, NotFoundError
from config.config import user_service_settings

# Simple cache implementation for now
class SimpleCache:
    """Simple in-memory cache for user service"""
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

logger = get_logger("user-service-db")

class UserDatabase:
    """User service database operations with caching"""

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
            logger.info("User database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize user database", extra={"error": str(e)})
            raise DatabaseError("init_db", f"Database initialization failed: {str(e)}")

    async def close_db(self):
        """Close database connection"""
        if self.client:
            self.client.close()
        await self.cache.close()
        self._initialized = False
        logger.info("User database connection closed")

    async def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # User profiles indexes
            await self.db.user_profiles.create_index("user_id", unique=True)
            await self.db.user_profiles.create_index("skills")
            await self.db.user_profiles.create_index("learning_goals")

            # Career profiles indexes
            await self.db.career_profiles.create_index("user_id", unique=True)
            await self.db.career_profiles.create_index("target_roles")
            await self.db.career_profiles.create_index("skills_to_develop")

            # Study plans indexes
            await self.db.study_plans.create_index("user_id", unique=True)
            await self.db.study_plans.create_index("created_at")

            # Achievements indexes
            await self.db.achievements.create_index("user_id")
            await self.db.achievements.create_index("category")
            await self.db.achievements.create_index("earned_date")

            # Study sessions indexes
            await self.db.study_sessions.create_index("user_id")
            await self.db.study_sessions.create_index("session_date")
            await self.db.study_sessions.create_index([("user_id", 1), ("session_date", -1)])

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error("Failed to create database indexes", extra={"error": str(e)})

    # Profile operations
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile with caching"""
        cache_key = f"user_profile:{user_id}"

        # Try cache first
        cached_profile = await self.cache.get(cache_key)
        if cached_profile:
            return json.loads(cached_profile)

        # Get from database
        profile = await self.db.user_profiles.find_one({"user_id": user_id})
        if profile:
            # Cache the result
            await self.cache.set(cache_key, json.dumps(profile, default=str),
                               ttl=user_service_settings.profile_cache_ttl)

        return profile

    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile and invalidate cache"""
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.user_profiles.update_one(
                {"user_id": user_id},
                {"$set": updates},
                upsert=True
            )

            # Invalidate cache
            cache_key = f"user_profile:{user_id}"
            await self.cache.delete(cache_key)

            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error("Failed to update user profile", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_user_profile", f"Profile update failed: {str(e)}")

    # Career operations
    async def get_career_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get career profile"""
        return await self.db.career_profiles.find_one({"user_id": user_id})

    async def update_career_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update career profile"""
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.career_profiles.update_one(
                {"user_id": user_id},
                {"$set": updates},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error("Failed to update career profile", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_career_profile", f"Career profile update failed: {str(e)}")

    # Study plan operations
    async def get_study_plan(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get study plan with caching"""
        cache_key = f"study_plan:{user_id}"

        # Try cache first
        cached_plan = await self.cache.get(cache_key)
        if cached_plan:
            return json.loads(cached_plan)

        # Get from database
        plan = await self.db.study_plans.find_one({"user_id": user_id})
        if plan:
            # Cache the result
            await self.cache.set(cache_key, json.dumps(plan, default=str),
                               ttl=user_service_settings.study_plan_cache_ttl)

        return plan

    async def update_study_plan(self, user_id: str, plan_data: Dict[str, Any]) -> bool:
        """Update study plan and invalidate cache"""
        try:
            plan_data["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.study_plans.update_one(
                {"user_id": user_id},
                {"$set": plan_data},
                upsert=True
            )

            # Invalidate cache
            cache_key = f"study_plan:{user_id}"
            await self.cache.delete(cache_key)

            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error("Failed to update study plan", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_study_plan", f"Study plan update failed: {str(e)}")

    # Achievement operations
    async def get_user_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user achievements"""
        achievements = await self.db.achievements.find({"user_id": user_id}).to_list(100)
        return achievements

    async def add_achievement(self, user_id: str, achievement: Dict[str, Any]) -> str:
        """Add new achievement"""
        try:
            achievement["_id"] = str(self.db.achievements.insert_one(achievement).inserted_id)
            return achievement["_id"]
        except Exception as e:
            logger.error("Failed to add achievement", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("add_achievement", f"Achievement creation failed: {str(e)}")

    # Analytics operations
    async def get_user_analytics(self, user_id: str, timeframe: str = "month") -> Dict[str, Any]:
        """Get user learning analytics with caching"""
        cache_key = f"user_analytics:{user_id}:{timeframe}"

        # Try cache first
        cached_analytics = await self.cache.get(cache_key)
        if cached_analytics:
            return json.loads(cached_analytics)

        # Calculate analytics from database
        analytics = await self._calculate_user_analytics(user_id, timeframe)

        # Cache the result
        await self.cache.set(cache_key, json.dumps(analytics, default=str),
                           ttl=user_service_settings.analytics_cache_ttl)

        return analytics

    async def _calculate_user_analytics(self, user_id: str, timeframe: str) -> Dict[str, Any]:
        """Calculate user analytics from raw data"""
        # This would contain complex analytics calculations
        # For now, return basic structure
        return {
            "user_id": user_id,
            "timeframe": timeframe,
            "total_study_hours": 0,
            "courses_completed": 0,
            "average_progress": 0,
            "learning_streak": 0,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }

    # Study session operations
    async def add_study_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Add study session"""
        try:
            session_data["created_at"] = datetime.now(timezone.utc)
            result = await self.db.study_sessions.insert_one(session_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error("Failed to add study session", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("add_study_session", f"Study session creation failed: {str(e)}")

    async def get_study_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user study sessions"""
        sessions = await self.db.study_sessions.find({"user_id": user_id}).sort("created_at", -1).to_list(limit)
        return sessions

# Global database instance
user_db = UserDatabase()