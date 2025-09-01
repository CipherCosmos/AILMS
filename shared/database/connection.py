"""
Database Connection Management
Optimized connection pooling and lifecycle management
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from shared.config.config import settings
from shared.common.logging import get_logger

logger = get_logger("database-connection")

class DatabaseConnectionManager:
    """Manages database connections with proper pooling and error handling"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> AsyncIOMotorDatabase:
        """Establish database connection with optimized settings"""
        async with self._lock:
            if self.database is not None:
                return self.database

            try:
                # Create client with optimized connection settings
                self.client = AsyncIOMotorClient(
                    settings.mongo_url,
                    maxPoolSize=getattr(settings, 'db_connection_pool_size', 10),
                    minPoolSize=5,
                    maxIdleTimeMS=getattr(settings, 'db_connection_pool_recycle', 3600) * 1000,
                    maxConnecting=getattr(settings, 'db_connection_pool_size', 10),
                    retryWrites=True,
                    retryReads=True,
                    readPreference=getattr(settings, 'db_read_preference', 'primary'),
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=30000
                )

                # Test connection
                await self.client.admin.command('ping')

                self.database = self.client[settings.db_name]

                logger.info("Database connection established", extra={
                    "database": settings.db_name,
                    "pool_size": f"5-{getattr(settings, 'db_connection_pool_size', 10)}"
                })

                return self.database

            except Exception as e:
                logger.error("Database connection failed", extra={"error": str(e)})
                raise

    async def disconnect(self):
        """Close database connection"""
        async with self._lock:
            if self.client:
                self.client.close()
                self.client = None
                self.database = None
                logger.info("Database connection closed")

    async def health_check(self) -> dict:
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

# Global connection manager instance
_connection_manager = DatabaseConnectionManager()

async def init_database() -> AsyncIOMotorDatabase:
    """Initialize database connection"""
    return await _connection_manager.connect()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance with automatic connection management"""
    return await _connection_manager.connect()

async def close_connection():
    """Close database connection"""
    await _connection_manager.disconnect()

async def health_check() -> dict:
    """Database health check"""
    return await _connection_manager.health_check()

@asynccontextmanager
async def get_db_session():
    """Context manager for database sessions"""
    db = await get_database()
    session = await db.client.start_session()
    try:
        yield db, session
    finally:
        await session.end_session()