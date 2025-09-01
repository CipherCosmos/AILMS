"""
Enhanced database utilities for LMS microservices
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import PyMongoError, ConnectionFailure, OperationFailure
from shared.config.config import settings
from shared.common.errors import DatabaseError
from shared.common.logging import get_logger

logger = get_logger("common-database")

class DatabaseManager:
    """Enhanced database manager with connection pooling and error handling"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> AsyncIOMotorDatabase:
        """Connect to database with connection pooling"""
        async with self._connection_lock:
            if self.database is not None:
                return self.database

            try:
                # Create client with connection pooling settings
                self.client = AsyncIOMotorClient(
                    settings.mongo_url,
                    maxPoolSize=10,  # Maximum number of connections in pool
                    minPoolSize=5,   # Minimum number of connections in pool
                    maxIdleTimeMS=30000,  # Close connections after 30 seconds of inactivity
                    serverSelectionTimeoutMS=5000,  # Timeout for server selection
                    connectTimeoutMS=5000,  # Timeout for initial connection
                    retryWrites=True,
                    retryReads=True
                )

                # Test connection
                await self.client.admin.command('ping')

                self.database = self.client[settings.db_name]

                logger.info("Database connection established", extra={
                    "database": settings.db_name,
                    "pool_size": "5-10"
                })

                return self.database

            except ConnectionFailure as e:
                logger.error("Database connection failed", extra={"error": str(e)})
                raise DatabaseError("connect", f"Failed to connect to database: {str(e)}")
            except Exception as e:
                logger.error("Database initialization error", extra={"error": str(e)})
                raise DatabaseError("initialize", str(e))

    async def disconnect(self):
        """Close database connection"""
        async with self._connection_lock:
            if self.client:
                self.client.close()
                self.client = None
                self.database = None
                logger.info("Database connection closed")

    async def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            if not self.database:
                return {"status": "disconnected"}

            # Test database operation
            await self.database.command('ping')

            # Get basic stats
            stats = await self.database.command('dbStats')

            return {
                "status": "healthy",
                "database": stats.get("db"),
                "collections": stats.get("collections", 0),
                "objects": stats.get("objects", 0),
                "data_size": stats.get("dataSize", 0),
                "storage_size": stats.get("storageSize", 0)
            }

        except Exception as e:
            logger.error("Database health check failed", extra={"error": str(e)})
            return {"status": "unhealthy", "error": str(e)}

# Global database manager instance
db_manager = DatabaseManager()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance with automatic connection management"""
    return await db_manager.connect()

@asynccontextmanager
async def get_db_session():
    """Context manager for database sessions"""
    db = await get_database()
    session = await db.client.start_session()
    try:
        yield db, session
    finally:
        await session.end_session()

class DatabaseOperations:
    """Enhanced database operations with error handling"""

    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    async def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Find one document with error handling"""
        try:
            db = await get_database()
            collection = db[self.collection_name]
            return await collection.find_one(query, projection)
        except PyMongoError as e:
            logger.error("Database find_one error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("find_one", str(e))

    async def find_many(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None,
                       skip: int = 0, limit: Optional[int] = None, sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """Find multiple documents with error handling"""
        try:
            db = await get_database()
            collection = db[self.collection_name]

            cursor = collection.find(query, projection)

            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            if sort:
                cursor = cursor.sort(sort)

            return await cursor.to_list(length=None)
        except PyMongoError as e:
            logger.error("Database find_many error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("find_many", str(e))

    async def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert one document with error handling"""
        try:
            db = await get_database()
            collection = db[self.collection_name]

            # Ensure _id is set
            if "_id" not in document:
                import uuid
                document["_id"] = document.get("id", str(uuid.uuid4()))

            result = await collection.insert_one(document)
            logger.info("Document inserted", extra={
                "collection": self.collection_name,
                "document_id": str(result.inserted_id)
            })
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error("Database insert_one error", extra={
                "collection": self.collection_name,
                "error": str(e)
            })
            raise DatabaseError("insert_one", str(e))

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> bool:
        """Update one document with error handling"""
        try:
            db = await get_database()
            collection = db[self.collection_name]

            result = await collection.update_one(query, update, upsert=upsert)
            updated = result.modified_count > 0 or (upsert and result.upserted_id is not None)

            if updated:
                logger.info("Document updated", extra={
                    "collection": self.collection_name,
                    "query": query,
                    "modified_count": result.modified_count
                })

            return updated
        except PyMongoError as e:
            logger.error("Database update_one error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("update_one", str(e))

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete one document with error handling"""
        try:
            db = await get_database()
            collection = db[self.collection_name]

            result = await collection.delete_one(query)
            deleted = result.deleted_count > 0

            if deleted:
                logger.info("Document deleted", extra={
                    "collection": self.collection_name,
                    "query": query
                })

            return deleted
        except PyMongoError as e:
            logger.error("Database delete_one error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("delete_one", str(e))

    async def count_documents(self, query: Dict[str, Any]) -> int:
        """Count documents with error handling"""
        try:
            db = await get_database()
            collection = db[self.collection_name]
            return await collection.count_documents(query)
        except PyMongoError as e:
            logger.error("Database count_documents error", extra={
                "collection": self.collection_name,
                "query": query,
                "error": str(e)
            })
            raise DatabaseError("count_documents", str(e))

# Convenience functions
async def health_check() -> Dict[str, Any]:
    """Database health check"""
    return await db_manager.health_check()

async def close_connection():
    """Close database connection"""
    await db_manager.disconnect()

def _uuid() -> str:
    """Generate a unique UUID string"""
    import uuid
    return str(uuid.uuid4())

async def _require(collection_name: str, query: Dict[str, Any], error_message: str = "Document not found") -> Dict[str, Any]:
    """Helper function to get a document and raise NotFoundError if not found"""
    from shared.common.errors import NotFoundError

    db = await get_database()
    collection = db[collection_name]
    document = await collection.find_one(query)

    if not document:
        raise NotFoundError(collection_name, str(query))

    return document