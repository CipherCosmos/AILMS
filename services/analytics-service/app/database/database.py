"""
Analytics Service Database Operations
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import DatabaseError, NotFoundError
from config.config import analytics_service_settings

# Simple cache implementation for now
class SimpleCache:
    """Simple in-memory cache for analytics service"""
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

logger = get_logger("analytics-service-db")

class AnalyticsDatabase:
    """Analytics service database operations with caching"""

    def __init__(self):
        self.client = None
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
            logger.info("Analytics database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize analytics database", extra={"error": str(e)})
            raise DatabaseError("init_db", f"Database initialization failed: {str(e)}")

    async def close_db(self):
        """Close database connection"""
        if self.client:
            self.client.close()
        await self.cache.close()
        self._initialized = False
        logger.info("Analytics database connection closed")

    async def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # Course analytics indexes
            await self.db.course_analytics.create_index("course_id", unique=True)
            await self.db.course_analytics.create_index("last_updated")
            await self.db.course_analytics.create_index("enrollment_count")

            # Student analytics indexes
            await self.db.student_analytics.create_index("student_id", unique=True)
            await self.db.student_analytics.create_index("last_updated")
            await self.db.student_analytics.create_index("courses_enrolled")

            # Performance metrics indexes
            await self.db.performance_metrics.create_index("student_id")
            await self.db.performance_metrics.create_index("course_id")
            await self.db.performance_metrics.create_index("recorded_at")
            await self.db.performance_metrics.create_index([("student_id", 1), ("course_id", 1)])

            # Reports indexes
            await self.db.reports.create_index("report_type")
            await self.db.reports.create_index("generated_at")
            await self.db.reports.create_index("created_by")

            # Real-time data indexes
            await self.db.real_time_metrics.create_index("timestamp")
            await self.db.real_time_metrics.create_index("metric_type")
            await self.db.real_time_metrics.create_index([("timestamp", -1), ("metric_type", 1)])

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error("Failed to create database indexes", extra={"error": str(e)})

    # Course analytics operations
    async def get_course_analytics(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get course analytics with caching"""
        cache_key = f"course_analytics:{course_id}"

        # Try cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Get from database
        analytics = await self.db.course_analytics.find_one({"course_id": course_id})
        if analytics:
            # Cache the result
            await self.cache.set(cache_key, json.dumps(analytics, default=str),
                               ttl=analytics_service_settings.analytics_cache_ttl)

        return analytics

    async def update_course_analytics(self, course_id: str, analytics_data: Dict[str, Any]) -> bool:
        """Update course analytics and invalidate cache"""
        try:
            analytics_data["last_updated"] = datetime.now(timezone.utc)
            result = await self.db.course_analytics.update_one(
                {"course_id": course_id},
                {"$set": analytics_data},
                upsert=True
            )

            # Invalidate cache
            cache_key = f"course_analytics:{course_id}"
            await self.cache.delete(cache_key)

            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error("Failed to update course analytics", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("update_course_analytics", f"Course analytics update failed: {str(e)}")

    # Student analytics operations
    async def get_student_analytics(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get student analytics with caching"""
        cache_key = f"student_analytics:{student_id}"

        # Try cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # Get from database
        analytics = await self.db.student_analytics.find_one({"student_id": student_id})
        if analytics:
            # Cache the result
            await self.cache.set(cache_key, json.dumps(analytics, default=str),
                               ttl=analytics_service_settings.analytics_cache_ttl)

        return analytics

    async def update_student_analytics(self, student_id: str, analytics_data: Dict[str, Any]) -> bool:
        """Update student analytics and invalidate cache"""
        try:
            analytics_data["last_updated"] = datetime.now(timezone.utc)
            result = await self.db.student_analytics.update_one(
                {"student_id": student_id},
                {"$set": analytics_data},
                upsert=True
            )

            # Invalidate cache
            cache_key = f"student_analytics:{student_id}"
            await self.cache.delete(cache_key)

            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error("Failed to update student analytics", extra={
                "student_id": student_id,
                "error": str(e)
            })
            raise DatabaseError("update_student_analytics", f"Student analytics update failed: {str(e)}")

    # Performance metrics operations
    async def save_performance_metric(self, metric_data: Dict[str, Any]) -> str:
        """Save performance metric"""
        try:
            metric_data["recorded_at"] = datetime.now(timezone.utc)
            result = await self.db.performance_metrics.insert_one(metric_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error("Failed to save performance metric", extra={"error": str(e)})
            raise DatabaseError("save_performance_metric", f"Performance metric save failed: {str(e)}")

    async def get_performance_metrics(self, student_id: str, course_id: Optional[str] = None,
                                    limit: int = 100) -> List[Dict[str, Any]]:
        """Get performance metrics for student"""
        try:
            query = {"student_id": student_id}
            if course_id:
                query["course_id"] = course_id

            metrics = await self.db.performance_metrics.find(query).sort("recorded_at", -1).to_list(limit)
            return metrics
        except Exception as e:
            logger.error("Failed to get performance metrics", extra={
                "student_id": student_id,
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("get_performance_metrics", f"Performance metrics retrieval failed: {str(e)}")

    # Report operations
    async def save_report(self, report_data: Dict[str, Any]) -> str:
        """Save generated report"""
        try:
            report_data["generated_at"] = datetime.now(timezone.utc)
            result = await self.db.reports.insert_one(report_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error("Failed to save report", extra={"error": str(e)})
            raise DatabaseError("save_report", f"Report save failed: {str(e)}")

    async def get_reports(self, report_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get reports"""
        try:
            query = {}
            if report_type:
                query["report_type"] = report_type

            reports = await self.db.reports.find(query).sort("generated_at", -1).to_list(limit)
            return reports
        except Exception as e:
            logger.error("Failed to get reports", extra={
                "report_type": report_type,
                "error": str(e)
            })
            raise DatabaseError("get_reports", f"Reports retrieval failed: {str(e)}")

    # Real-time metrics operations
    async def save_real_time_metric(self, metric_data: Dict[str, Any]) -> str:
        """Save real-time metric"""
        try:
            metric_data["timestamp"] = datetime.now(timezone.utc)
            result = await self.db.real_time_metrics.insert_one(metric_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error("Failed to save real-time metric", extra={"error": str(e)})
            raise DatabaseError("save_real_time_metric", f"Real-time metric save failed: {str(e)}")

    async def get_real_time_metrics(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get real-time metrics for the last N hours"""
        try:
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            metrics = await self.db.real_time_metrics.find({
                "metric_type": metric_type,
                "timestamp": {"$gte": start_time}
            }).sort("timestamp", -1).to_list(1000)
            return metrics
        except Exception as e:
            logger.error("Failed to get real-time metrics", extra={
                "metric_type": metric_type,
                "hours": hours,
                "error": str(e)
            })
            raise DatabaseError("get_real_time_metrics", f"Real-time metrics retrieval failed: {str(e)}")

    # Analytics aggregation operations
    async def aggregate_course_performance(self, course_id: str) -> Dict[str, Any]:
        """Aggregate performance data for a course"""
        try:
            pipeline = [
                {"$match": {"course_id": course_id}},
                {"$group": {
                    "_id": None,
                    "total_students": {"$sum": 1},
                    "avg_performance": {"$avg": "$performance_score"},
                    "completion_rate": {"$avg": "$completion_percentage"},
                    "total_study_hours": {"$sum": "$study_hours"}
                }}
            ]

            result = await self.db.performance_metrics.aggregate(pipeline).to_list(1)
            return result[0] if result else {}

        except Exception as e:
            logger.error("Failed to aggregate course performance", extra={
                "course_id": course_id,
                "error": str(e)
            })
            raise DatabaseError("aggregate_course_performance", f"Course performance aggregation failed: {str(e)}")

    async def aggregate_student_performance(self, student_id: str) -> Dict[str, Any]:
        """Aggregate performance data for a student"""
        try:
            pipeline = [
                {"$match": {"student_id": student_id}},
                {"$group": {
                    "_id": None,
                    "total_courses": {"$sum": 1},
                    "avg_performance": {"$avg": "$performance_score"},
                    "total_study_hours": {"$sum": "$study_hours"},
                    "courses_completed": {"$sum": {"$cond": [{"$eq": ["$completion_percentage", 100]}, 1, 0]}}
                }}
            ]

            result = await self.db.performance_metrics.aggregate(pipeline).to_list(1)
            return result[0] if result else {}

        except Exception as e:
            logger.error("Failed to aggregate student performance", extra={
                "student_id": student_id,
                "error": str(e)
            })
            raise DatabaseError("aggregate_student_performance", f"Student performance aggregation failed: {str(e)}")

# Global database instance
analytics_db = AnalyticsDatabase()