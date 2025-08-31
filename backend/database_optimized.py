"""
Optimized database operations with connection pooling and query optimization.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from motor.core import AgnosticCollection
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager
from performance_config import performance_settings
import time
import logging

logger = logging.getLogger(__name__)

class OptimizedDatabase:
    """Optimized database client with connection pooling and performance monitoring."""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._query_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def initialize(self, mongo_url: str, db_name: str):
        """Initialize optimized database connection."""
        try:
            self.client = AsyncIOMotorClient(
                mongo_url,
                maxPoolSize=performance_settings.db_connection_pool_size,
                maxIdleTimeMS=performance_settings.db_pool_recycle * 1000,
                maxConnecting=performance_settings.db_connection_pool_size,
                retryWrites=True,
                retryReads=True,
                readPreference=performance_settings.db_read_preference,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000
            )

            self.db = self.client[db_name]

            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Optimized database connection established")

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise

    async def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")

    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        session = await self.client.start_session()
        try:
            async with session.start_transaction():
                yield session
        except Exception as e:
            await session.abort_transaction()
            raise
        finally:
            await session.end_session()

    def collection(self, name: str) -> AgnosticCollection:
        """Get collection with performance monitoring."""
        if not self.db:
            raise RuntimeError("Database not initialized")

        return OptimizedCollection(self.db[name], self._query_stats)

class OptimizedCollection:
    """Optimized collection with query performance monitoring."""

    def __init__(self, collection: AgnosticCollection, stats_dict: Dict[str, Dict[str, Any]]):
        self.collection = collection
        self._stats = stats_dict
        self._collection_name = collection.name

    async def find_one(self, filter: Dict[str, Any], *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Optimized find_one with timing."""
        start_time = time.time()
        try:
            result = await self.collection.find_one(filter, *args, **kwargs)
            self._record_query_time("find_one", time.time() - start_time)
            return result
        except Exception as e:
            self._record_error("find_one", str(e))
            raise

    async def find(self, filter: Dict[str, Any] = None, *args, **kwargs):
        """Optimized find with timing."""
        start_time = time.time()
        try:
            cursor = self.collection.find(filter or {}, *args, **kwargs)
            # Add timeout
            cursor.max_time_ms(performance_settings.db_query_timeout_seconds * 1000)
            result = await cursor.to_list(length=None)
            self._record_query_time("find", time.time() - start_time, len(result))
            return result
        except Exception as e:
            self._record_error("find", str(e))
            raise

    async def insert_one(self, document: Dict[str, Any], *args, **kwargs) -> str:
        """Optimized insert_one with timing."""
        start_time = time.time()
        try:
            result = await self.collection.insert_one(document, *args, **kwargs)
            self._record_query_time("insert_one", time.time() - start_time)
            return str(result.inserted_id)
        except Exception as e:
            self._record_error("insert_one", str(e))
            raise

    async def insert_many(self, documents: List[Dict[str, Any]], *args, **kwargs):
        """Optimized insert_many with timing."""
        start_time = time.time()
        try:
            result = await self.collection.insert_many(documents, *args, **kwargs)
            self._record_query_time("insert_many", time.time() - start_time, len(documents))
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            self._record_error("insert_many", str(e))
            raise

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], *args, **kwargs):
        """Optimized update_one with timing."""
        start_time = time.time()
        try:
            result = await self.collection.update_one(filter, update, *args, **kwargs)
            self._record_query_time("update_one", time.time() - start_time)
            return result
        except Exception as e:
            self._record_error("update_one", str(e))
            raise

    async def update_many(self, filter: Dict[str, Any], update: Dict[str, Any], *args, **kwargs):
        """Optimized update_many with timing."""
        start_time = time.time()
        try:
            result = await self.collection.update_many(filter, update, *args, **kwargs)
            self._record_query_time("update_many", time.time() - start_time)
            return result
        except Exception as e:
            self._record_error("update_many", str(e))
            raise

    async def delete_one(self, filter: Dict[str, Any], *args, **kwargs):
        """Optimized delete_one with timing."""
        start_time = time.time()
        try:
            result = await self.collection.delete_one(filter, *args, **kwargs)
            self._record_query_time("delete_one", time.time() - start_time)
            return result
        except Exception as e:
            self._record_error("delete_one", str(e))
            raise

    async def delete_many(self, filter: Dict[str, Any], *args, **kwargs):
        """Optimized delete_many with timing."""
        start_time = time.time()
        try:
            result = await self.collection.delete_many(filter, *args, **kwargs)
            self._record_query_time("delete_many", time.time() - start_time)
            return result
        except Exception as e:
            self._record_error("delete_many", str(e))
            raise

    async def count_documents(self, filter: Dict[str, Any] = None, *args, **kwargs) -> int:
        """Optimized count_documents with timing."""
        start_time = time.time()
        try:
            result = await self.collection.count_documents(filter or {}, *args, **kwargs)
            self._record_query_time("count_documents", time.time() - start_time)
            return result
        except Exception as e:
            self._record_error("count_documents", str(e))
            raise

    async def aggregate(self, pipeline: List[Dict[str, Any]], *args, **kwargs):
        """Optimized aggregation with timing."""
        start_time = time.time()
        try:
            cursor = self.collection.aggregate(pipeline, *args, **kwargs)
            cursor.max_time_ms(performance_settings.db_query_timeout_seconds * 1000)
            result = await cursor.to_list(length=None)
            self._record_query_time("aggregate", time.time() - start_time, len(result))
            return result
        except Exception as e:
            self._record_error("aggregate", str(e))
            raise

    def _record_query_time(self, operation: str, duration: float, record_count: int = 1):
        """Record query performance statistics."""
        key = f"{self._collection_name}:{operation}"
        if key not in self._stats:
            self._stats[key] = {
                "total_queries": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0,
                "min_time": float('inf'),
                "total_records": 0,
                "errors": 0
            }

        stats = self._stats[key]
        stats["total_queries"] += 1
        stats["total_time"] += duration
        stats["avg_time"] = stats["total_time"] / stats["total_queries"]
        stats["max_time"] = max(stats["max_time"], duration)
        stats["min_time"] = min(stats["min_time"], duration)
        stats["total_records"] += record_count

    def _record_error(self, operation: str, error: str):
        """Record query errors."""
        key = f"{self._collection_name}:{operation}"
        if key not in self._stats:
            self._stats[key] = {
                "total_queries": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0,
                "min_time": float('inf'),
                "total_records": 0,
                "errors": 0
            }

        self._stats[key]["errors"] += 1
        logger.warning(f"Database error in {key}: {error}")

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics."""
        return self._stats.copy()

# Global optimized database instance
optimized_db = OptimizedDatabase()

# Database indexes for performance
async def create_database_indexes(db: AsyncIOMotorDatabase):
    """Create optimized database indexes."""

    indexes = [
        # Users collection
        ("users", [("email", 1)], {"unique": True}),
        ("users", [("role", 1)]),
        ("users", [("created_at", -1)]),

        # Courses collection
        ("courses", [("owner_id", 1)]),
        ("courses", [("published", 1)]),
        ("courses", [("enrolled_user_ids", 1)]),
        ("courses", [("created_at", -1)]),
        ("courses", [("title", "text"), ("description", "text")]),

        # Course progress collection
        ("course_progress", [("course_id", 1), ("user_id", 1)], {"unique": True}),
        ("course_progress", [("user_id", 1)]),
        ("course_progress", [("completed", 1)]),

        # Assignments collection
        ("assignments", [("course_id", 1)]),
        ("assignments", [("due_at", 1)]),
        ("assignments", [("created_at", -1)]),

        # Submissions collection
        ("submissions", [("assignment_id", 1)]),
        ("submissions", [("user_id", 1)]),
        ("submissions", [("created_at", -1)]),

        # Notifications collection
        ("notifications", [("user_id", 1)]),
        ("notifications", [("read", 1)]),
        ("notifications", [("created_at", -1)]),

        # Discussions collection
        ("discussions", [("course_id", 1)]),
        ("discussions", [("user_id", 1)]),
        ("discussions", [("created_at", -1)]),

        # Analytics collection
        ("course_analytics", [("course_id", 1)]),
        ("course_analytics", [("last_updated", -1)])
    ]

    for collection_name, keys, options in indexes:
        try:
            collection = db[collection_name]
            await collection.create_index(keys, **options)
            logger.info(f"✅ Created index on {collection_name}: {keys}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to create index on {collection_name}: {e}")

# Query optimization helpers
def optimize_course_query(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize course queries with proper indexing hints."""
    optimized_filters = filters.copy()

    # Add projection to limit fields if not specified
    if "projection" not in optimized_filters:
        optimized_filters["projection"] = {
            "_id": 1,
            "title": 1,
            "audience": 1,
            "difficulty": 1,
            "published": 1,
            "owner_id": 1,
            "created_at": 1,
            "enrolled_user_ids": 1
        }

    return optimized_filters

def optimize_user_query(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize user queries."""
    optimized_filters = filters.copy()

    if "projection" not in optimized_filters:
        optimized_filters["projection"] = {
            "_id": 1,
            "email": 1,
            "name": 1,
            "role": 1,
            "created_at": 1
        }

    return optimized_filters