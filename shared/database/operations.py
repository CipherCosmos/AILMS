"""
Database Operations with Error Handling and Performance Monitoring
"""

import time
from typing import Dict, Any, List, Optional, Union
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.collection import Collection
from pymongo.errors import PyMongoError, ConnectionFailure, OperationFailure

from shared.common.errors import DatabaseError
from shared.common.logging import get_logger
from .connection import get_database

logger = get_logger("database-operations")

class DatabaseOperations:
    """Enhanced database operations with error handling and monitoring"""

    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self._query_stats = {}

    async def _get_collection(self):
        """Get collection instance"""
        db = await get_database()
        return db[self.collection_name]

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Find one document with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()
            result = await collection.find_one(query, projection)
            self._record_query_time("find_one", time.time() - start_time)
            return result
        except PyMongoError as e:
            self._record_error("find_one", str(e))
            logger.error("Database find_one error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("find_one", str(e))

    async def find_many(self, query: Dict[str, Any] = None, projection: Optional[Dict[str, Any]] = None,
                       skip: int = 0, limit: Optional[int] = None, sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """Find multiple documents with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()
            cursor = collection.find(query or {}, projection)

            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            if sort:
                cursor = cursor.sort(sort)

            # Add timeout for long-running queries
            cursor.max_time_ms(30000)  # 30 seconds

            result = await cursor.to_list(length=None)
            self._record_query_time("find_many", time.time() - start_time, len(result))
            return result
        except PyMongoError as e:
            self._record_error("find_many", str(e))
            logger.error("Database find_many error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("find_many", str(e))

    async def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert one document with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()

            # Ensure _id is set
            if "_id" not in document:
                from shared.database.database import _uuid
                document["_id"] = document.get("id", _uuid())

            result = await collection.insert_one(document)
            self._record_query_time("insert_one", time.time() - start_time)

            logger.info("Document inserted", extra={
                "collection": self.collection_name,
                "document_id": str(result.inserted_id)
            })

            return str(result.inserted_id)
        except PyMongoError as e:
            self._record_error("insert_one", str(e))
            logger.error("Database insert_one error", extra={
                "collection": self.collection_name,
                "error": str(e)
            })
            raise DatabaseError("insert_one", str(e))

    async def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple documents with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()

            # Ensure all documents have _id
            for doc in documents:
                if "_id" not in doc:
                    from shared.database.database import _uuid
                    doc["_id"] = doc.get("id", _uuid())

            result = await collection.insert_many(documents)
            self._record_query_time("insert_many", time.time() - start_time, len(documents))

            logger.info("Documents inserted", extra={
                "collection": self.collection_name,
                "count": len(result.inserted_ids)
            })

            return [str(id) for id in result.inserted_ids]
        except PyMongoError as e:
            self._record_error("insert_many", str(e))
            logger.error("Database insert_many error", extra={
                "collection": self.collection_name,
                "error": str(e)
            })
            raise DatabaseError("insert_many", str(e))

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> bool:
        """Update one document with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()

            result = await collection.update_one(query, update, upsert=upsert)
            updated = result.modified_count > 0 or (upsert and result.upserted_id is not None)
            self._record_query_time("update_one", time.time() - start_time)

            if updated:
                logger.info("Document updated", extra={
                    "collection": self.collection_name,
                    "query": query,
                    "modified_count": result.modified_count
                })

            return updated
        except PyMongoError as e:
            self._record_error("update_one", str(e))
            logger.error("Database update_one error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("update_one", str(e))

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """Update multiple documents with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()

            result = await collection.update_many(query, update)
            self._record_query_time("update_many", time.time() - start_time, result.modified_count)

            logger.info("Documents updated", extra={
                "collection": self.collection_name,
                "query": query,
                "modified_count": result.modified_count
            })

            return result.modified_count
        except PyMongoError as e:
            self._record_error("update_many", str(e))
            logger.error("Database update_many error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("update_many", str(e))

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete one document with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()

            result = await collection.delete_one(query)
            deleted = result.deleted_count > 0
            self._record_query_time("delete_one", time.time() - start_time)

            if deleted:
                logger.info("Document deleted", extra={
                    "collection": self.collection_name,
                    "query": query
                })

            return deleted
        except PyMongoError as e:
            self._record_error("delete_one", str(e))
            logger.error("Database delete_one error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("delete_one", str(e))

    async def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()

            result = await collection.delete_many(query)
            self._record_query_time("delete_many", time.time() - start_time, result.deleted_count)

            logger.info("Documents deleted", extra={
                "collection": self.collection_name,
                "query": query,
                "deleted_count": result.deleted_count
            })

            return result.deleted_count
        except PyMongoError as e:
            self._record_error("delete_many", str(e))
            logger.error("Database delete_many error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("delete_many", str(e))

    async def count_documents(self, query: Dict[str, Any] = None) -> int:
        """Count documents with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()
            result = await collection.count_documents(query or {})
            self._record_query_time("count_documents", time.time() - start_time)
            return result
        except PyMongoError as e:
            self._record_error("count_documents", str(e))
            logger.error("Database count_documents error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("count_documents", str(e))

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate documents with error handling and timing"""
        start_time = time.time()
        try:
            collection = await self._get_collection()
            cursor = collection.aggregate(pipeline)
            cursor.max_time_ms(30000)  # 30 seconds timeout
            result = await cursor.to_list(length=None)
            self._record_query_time("aggregate", time.time() - start_time, len(result))
            return result
        except PyMongoError as e:
            self._record_error("aggregate", str(e))
            logger.error("Database aggregate error", extra={
                "collection": self.collection_name,
                "pipeline": pipeline,
                "error": str(e)
            })
            raise DatabaseError("aggregate", str(e))

    def _record_query_time(self, operation: str, duration: float, record_count: int = 1):
        """Record query performance statistics"""
        key = f"{self.collection_name}:{operation}"
        if key not in self._query_stats:
            self._query_stats[key] = {
                "total_queries": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0,
                "min_time": float('inf'),
                "total_records": 0,
                "errors": 0
            }

        stats = self._query_stats[key]
        stats["total_queries"] += 1
        stats["total_time"] += duration
        stats["avg_time"] = stats["total_time"] / stats["total_queries"]
        stats["max_time"] = max(stats["max_time"], duration)
        stats["min_time"] = min(stats["min_time"], duration)
        stats["total_records"] += record_count

    def _record_error(self, operation: str, error: str):
        """Record query errors"""
        key = f"{self.collection_name}:{operation}"
        if key not in self._query_stats:
            self._query_stats[key] = {
                "total_queries": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0,
                "min_time": float('inf'),
                "total_records": 0,
                "errors": 0
            }

        self._query_stats[key]["errors"] += 1
        logger.warning(f"Database error in {key}: {error}")

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics"""
        return self._query_stats.copy()