"""
Course Service Database Operations
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import DatabaseError, NotFoundError
from config.config import course_service_settings

# Simple cache implementation for now
class SimpleCache:
    """Simple in-memory cache for course service"""
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

logger = get_logger("course-service-db")

class CourseDatabase:
    """Course service database operations with caching"""

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
            logger.info("Course database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize course database", extra={"error": str(e)})
            raise DatabaseError("init_db", f"Database initialization failed: {str(e)}")

    async def close_db(self):
        """Close database connection"""
        if self.client:
            self.client.close()
        await self.cache.close()
        self._initialized = False
        logger.info("Course database connection closed")

    async def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # Courses indexes
            await self.db.courses.create_index("owner_id")
            await self.db.courses.create_index("published")
            await self.db.courses.create_index("enrolled_user_ids")
            await self.db.courses.create_index("audience")
            await self.db.courses.create_index("difficulty")
            await self.db.courses.create_index("created_at")
            await self.db.courses.create_index("updated_at")

            # Lessons indexes
            await self.db.lessons.create_index("course_id")
            await self.db.lessons.create_index("order")
            await self.db.lessons.create_index([("course_id", 1), ("order", 1)])

            # Course progress indexes
            await self.db.course_progress.create_index("user_id")
            await self.db.course_progress.create_index("course_id")
            await self.db.course_progress.create_index([("user_id", 1), ("course_id", 1)])
            await self.db.course_progress.create_index("completed")
            await self.db.course_progress.create_index("last_accessed")

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error("Failed to create database indexes", extra={"error": str(e)})

    # Course operations
    async def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get course with caching"""
        cache_key = f"course:{course_id}"

        # Try cache first
        cached_course = await self.cache.get(cache_key)
        if cached_course:
            return json.loads(cached_course)

        # Get from database
        course = await self.db.courses.find_one({"_id": course_id})
        if course:
            # Cache the result
            await self.cache.set(cache_key, json.dumps(course, default=str),
                               ttl=course_service_settings.course_cache_ttl)

        return course

    async def create_course(self, course_data: Dict[str, Any]) -> str:
        """Create new course"""
        try:
            course_data["created_at"] = datetime.now(timezone.utc)
            course_data["updated_at"] = datetime.now(timezone.utc)

            result = await self.db.courses.insert_one(course_data)
            course_id = str(result.inserted_id)

            logger.info("Course created in database", extra={"course_id": course_id})
            return course_id

        except Exception as e:
            logger.error("Failed to create course", extra={"error": str(e)})
            raise DatabaseError("create_course", f"Course creation failed: {str(e)}")

    async def update_course(self, course_id: str, updates: Dict[str, Any]) -> bool:
        """Update course and invalidate cache"""
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.courses.update_one(
                {"_id": course_id},
                {"$set": updates}
            )

            # Invalidate cache
            cache_key = f"course:{course_id}"
            await self.cache.delete(cache_key)

            return result.modified_count > 0

        except Exception as e:
            logger.error("Failed to update course", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("update_course", f"Course update failed: {str(e)}")

    async def list_courses(self, query: Dict[str, Any], limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List courses with filtering"""
        try:
            courses = await self.db.courses.find(query).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
            return courses

        except Exception as e:
            logger.error("Failed to list courses", extra={"error": str(e)})
            raise DatabaseError("list_courses", f"Course listing failed: {str(e)}")

    async def enroll_user(self, course_id: str, user_id: str) -> bool:
        """Enroll user in course"""
        try:
            result = await self.db.courses.update_one(
                {"_id": course_id},
                {"$addToSet": {"enrolled_user_ids": user_id}}
            )

            # Invalidate course cache
            cache_key = f"course:{course_id}"
            await self.cache.delete(cache_key)

            return result.modified_count > 0

        except Exception as e:
            logger.error("Failed to enroll user", extra={
                "course_id": course_id,
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("enroll_user", f"User enrollment failed: {str(e)}")

    async def unenroll_user(self, course_id: str, user_id: str) -> bool:
        """Unenroll user from course"""
        try:
            result = await self.db.courses.update_one(
                {"_id": course_id},
                {"$pull": {"enrolled_user_ids": user_id}}
            )

            # Invalidate course cache
            cache_key = f"course:{course_id}"
            await self.cache.delete(cache_key)

            return result.modified_count > 0

        except Exception as e:
            logger.error("Failed to unenroll user", extra={
                "course_id": course_id,
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("unenroll_user", f"User unenrollment failed: {str(e)}")

    # Lesson operations
    async def get_lesson(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get lesson with caching"""
        cache_key = f"lesson:{lesson_id}"

        # Try cache first
        cached_lesson = await self.cache.get(cache_key)
        if cached_lesson:
            return json.loads(cached_lesson)

        # Get from database
        lesson = await self.db.lessons.find_one({"_id": lesson_id})
        if lesson:
            # Cache the result
            await self.cache.set(cache_key, json.dumps(lesson, default=str),
                               ttl=course_service_settings.lesson_cache_ttl)

        return lesson

    async def get_course_lessons(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all lessons for a course"""
        try:
            lessons = await self.db.lessons.find({"course_id": course_id}).sort("order", 1).to_list(100)
            return lessons

        except Exception as e:
            logger.error("Failed to get course lessons", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_course_lessons", f"Course lessons retrieval failed: {str(e)}")

    # Progress operations
    async def get_user_progress(self, user_id: str, course_id: str) -> Optional[Dict[str, Any]]:
        """Get user progress for a course"""
        try:
            progress = await self.db.course_progress.find_one({
                "user_id": user_id,
                "course_id": course_id
            })
            return progress

        except Exception as e:
            logger.error("Failed to get user progress", extra={
                "user_id": user_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_user_progress", f"User progress retrieval failed: {str(e)}")

    async def update_user_progress(self, user_id: str, course_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update user progress for a course"""
        try:
            progress_data["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.course_progress.update_one(
                {"user_id": user_id, "course_id": course_id},
                {"$set": progress_data},
                upsert=True
            )

            return result.modified_count > 0 or result.upserted_id is not None

        except Exception as e:
            logger.error("Failed to update user progress", extra={
                "user_id": user_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("update_user_progress", f"User progress update failed: {str(e)}")

    # Statistics operations
    async def get_course_stats(self) -> Dict[str, Any]:
        """Get course statistics"""
        try:
            # Get course counts
            total_courses = await self.db.courses.count_documents({})
            published_courses = await self.db.courses.count_documents({"published": True})

            # Get enrollment statistics
            pipeline = [
                {"$group": {"_id": None, "total_enrollments": {"$sum": {"$size": "$enrolled_user_ids"}}}}
            ]
            enrollment_result = await self.db.courses.aggregate(pipeline).to_list(1)
            total_enrollments = enrollment_result[0]["total_enrollments"] if enrollment_result else 0

            return {
                "total_courses": total_courses,
                "published_courses": published_courses,
                "draft_courses": total_courses - published_courses,
                "total_enrollments": total_enrollments,
                "average_enrollment_per_course": round(total_enrollments / max(total_courses, 1), 1)
            }

        except Exception as e:
            logger.error("Failed to get course stats", extra={"error": str(e)})
            raise DatabaseError("get_course_stats", f"Course stats retrieval failed: {str(e)}")

# Global database instance
course_db = CourseDatabase()