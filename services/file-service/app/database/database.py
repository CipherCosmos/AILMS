"""
File Service Database Operations
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json
import os

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import DatabaseError, NotFoundError
from config.config import file_service_settings

# Simple cache implementation for now
class SimpleCache:
    """Simple in-memory cache for file service"""
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

logger = get_logger("file-service-db")

class FileDatabase:
    """File service database operations with caching"""

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
            logger.info("File database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize file database", extra={"error": str(e)})
            raise DatabaseError("init_db", f"Database initialization failed: {str(e)}")

    async def close_db(self):
        """Close database connection"""
        if self.client:
            self.client.close()
        await self.cache.close()
        self._initialized = False
        logger.info("File database connection closed")

    async def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # Files indexes
            await self.db.files.create_index("file_id", unique=True)
            await self.db.files.create_index("user_id")
            await self.db.files.create_index("filename")
            await self.db.files.create_index("uploaded_at")
            await self.db.files.create_index("file_type")
            await self.db.files.create_index([("user_id", 1), ("uploaded_at", -1)])
            await self.db.files.create_index([("user_id", 1), ("file_type", 1)])

            # File versions indexes
            await self.db.file_versions.create_index("file_id")
            await self.db.file_versions.create_index("version_number")
            await self.db.file_versions.create_index([("file_id", 1), ("version_number", -1)])

            # Shared links indexes
            await self.db.shared_links.create_index("file_id")
            await self.db.shared_links.create_index("share_token", unique=True)
            await self.db.shared_links.create_index("expires_at")
            await self.db.shared_links.create_index("created_by")

            # File access logs indexes
            await self.db.file_access_logs.create_index("file_id")
            await self.db.file_access_logs.create_index("user_id")
            await self.db.file_access_logs.create_index("accessed_at")
            await self.db.file_access_logs.create_index([("file_id", 1), ("accessed_at", -1)])

            # Thumbnails indexes
            await self.db.thumbnails.create_index("file_id")
            await self.db.thumbnails.create_index("size")

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error("Failed to create database indexes", extra={"error": str(e)})

    # File operations
    async def save_file_metadata(self, file_data: Dict[str, Any]) -> str:
        """Save file metadata"""
        try:
            file_data["uploaded_at"] = datetime.now(timezone.utc)
            file_data["updated_at"] = datetime.now(timezone.utc)

            result = await self.db.files.insert_one(file_data)
            file_id = str(result.inserted_id)

            logger.info("File metadata saved", extra={"file_id": file_id})
            return file_id

        except Exception as e:
            logger.error("Failed to save file metadata", extra={"error": str(e)})
            raise DatabaseError("save_file_metadata", f"File metadata save failed: {str(e)}")

    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata by ID"""
        try:
            file_data = await self.db.files.find_one({"file_id": file_id})
            return file_data

        except Exception as e:
            logger.error("Failed to get file metadata", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("get_file_metadata", f"File metadata retrieval failed: {str(e)}")

    async def get_user_files(self, user_id: str, limit: int = 50, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's files"""
        try:
            query = {"user_id": user_id}
            if file_type:
                query["file_type"] = file_type

            files = await self.db.files.find(query).sort("uploaded_at", -1).to_list(limit)
            return files

        except Exception as e:
            logger.error("Failed to get user files", extra={
                "user_id": user_id,
                "file_type": file_type,
                "error": str(e)
            })
            raise DatabaseError("get_user_files", f"User files retrieval failed: {str(e)}")

    async def update_file_metadata(self, file_id: str, updates: Dict[str, Any]) -> bool:
        """Update file metadata"""
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.files.update_one(
                {"file_id": file_id},
                {"$set": updates}
            )

            success = result.modified_count > 0
            if success:
                logger.info("File metadata updated", extra={"file_id": file_id})

            return success

        except Exception as e:
            logger.error("Failed to update file metadata", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("update_file_metadata", f"File metadata update failed: {str(e)}")

    async def delete_file_metadata(self, file_id: str) -> bool:
        """Delete file metadata"""
        try:
            result = await self.db.files.delete_one({"file_id": file_id})

            success = result.deleted_count > 0
            if success:
                logger.info("File metadata deleted", extra={"file_id": file_id})

            return success

        except Exception as e:
            logger.error("Failed to delete file metadata", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("delete_file_metadata", f"File metadata deletion failed: {str(e)}")

    # File version operations
    async def save_file_version(self, version_data: Dict[str, Any]) -> str:
        """Save file version"""
        try:
            version_data["created_at"] = datetime.now(timezone.utc)
            result = await self.db.file_versions.insert_one(version_data)
            version_id = str(result.inserted_id)

            return version_id

        except Exception as e:
            logger.error("Failed to save file version", extra={"error": str(e)})
            raise DatabaseError("save_file_version", f"File version save failed: {str(e)}")

    async def get_file_versions(self, file_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get file versions"""
        try:
            versions = await self.db.file_versions.find({"file_id": file_id}).sort("version_number", -1).to_list(limit)
            return versions

        except Exception as e:
            logger.error("Failed to get file versions", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("get_file_versions", f"File versions retrieval failed: {str(e)}")

    # Shared links operations
    async def create_shared_link(self, link_data: Dict[str, Any]) -> str:
        """Create shared link"""
        try:
            link_data["created_at"] = datetime.now(timezone.utc)
            link_data["expires_at"] = link_data.get("expires_at", datetime.now(timezone.utc) + timedelta(days=7))

            result = await self.db.shared_links.insert_one(link_data)
            link_id = str(result.inserted_id)

            logger.info("Shared link created", extra={"link_id": link_id})
            return link_id

        except Exception as e:
            logger.error("Failed to create shared link", extra={"error": str(e)})
            raise DatabaseError("create_shared_link", f"Shared link creation failed: {str(e)}")

    async def get_shared_link(self, share_token: str) -> Optional[Dict[str, Any]]:
        """Get shared link by token"""
        try:
            link_data = await self.db.shared_links.find_one({"share_token": share_token})
            if link_data and link_data.get("expires_at", datetime.max.replace(tzinfo=timezone.utc)) > datetime.now(timezone.utc):
                return link_data
            return None

        except Exception as e:
            logger.error("Failed to get shared link", extra={
                "share_token": share_token,
                "error": str(e)
            })
            raise DatabaseError("get_shared_link", f"Shared link retrieval failed: {str(e)}")

    async def get_file_shared_links(self, file_id: str) -> List[Dict[str, Any]]:
        """Get shared links for a file"""
        try:
            links = await self.db.shared_links.find({"file_id": file_id}).to_list(20)
            return links

        except Exception as e:
            logger.error("Failed to get file shared links", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("get_file_shared_links", f"File shared links retrieval failed: {str(e)}")

    # Access logging operations
    async def log_file_access(self, access_data: Dict[str, Any]) -> str:
        """Log file access"""
        try:
            access_data["accessed_at"] = datetime.now(timezone.utc)
            result = await self.db.file_access_logs.insert_one(access_data)
            access_id = str(result.inserted_id)

            return access_id

        except Exception as e:
            logger.error("Failed to log file access", extra={"error": str(e)})
            return ""

    async def get_file_access_logs(self, file_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get file access logs"""
        try:
            logs = await self.db.file_access_logs.find({"file_id": file_id}).sort("accessed_at", -1).to_list(limit)
            return logs

        except Exception as e:
            logger.error("Failed to get file access logs", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("get_file_access_logs", f"File access logs retrieval failed: {str(e)}")

    # Thumbnail operations
    async def save_thumbnail(self, thumbnail_data: Dict[str, Any]) -> str:
        """Save thumbnail metadata"""
        try:
            thumbnail_data["created_at"] = datetime.now(timezone.utc)
            result = await self.db.thumbnails.insert_one(thumbnail_data)
            thumbnail_id = str(result.inserted_id)

            return thumbnail_id

        except Exception as e:
            logger.error("Failed to save thumbnail", extra={"error": str(e)})
            raise DatabaseError("save_thumbnail", f"Thumbnail save failed: {str(e)}")

    async def get_file_thumbnails(self, file_id: str) -> List[Dict[str, Any]]:
        """Get thumbnails for a file"""
        try:
            thumbnails = await self.db.thumbnails.find({"file_id": file_id}).to_list(10)
            return thumbnails

        except Exception as e:
            logger.error("Failed to get file thumbnails", extra={
                "file_id": file_id,
                "error": str(e)
            })
            raise DatabaseError("get_file_thumbnails", f"File thumbnails retrieval failed: {str(e)}")

    # Analytics operations
    async def get_storage_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            match_stage = {}
            if user_id:
                match_stage["user_id"] = user_id

            pipeline = [
                {"$match": match_stage},
                {"$group": {
                    "_id": None,
                    "total_files": {"$sum": 1},
                    "total_size": {"$sum": "$file_size"},
                    "file_types": {"$addToSet": "$file_type"}
                }}
            ]

            result = await self.db.files.aggregate(pipeline).to_list(1)
            stats = result[0] if result else {
                "total_files": 0,
                "total_size": 0,
                "file_types": []
            }

            return stats

        except Exception as e:
            logger.error("Failed to get storage stats", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_storage_stats", f"Storage stats retrieval failed: {str(e)}")

    async def get_upload_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get upload statistics"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            pipeline = [
                {"$match": {"uploaded_at": {"$gte": start_date}}},
                {"$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$uploaded_at"}},
                        "file_type": "$file_type"
                    },
                    "count": {"$sum": 1},
                    "total_size": {"$sum": "$file_size"}
                }},
                {"$sort": {"_id.date": -1}}
            ]

            results = await self.db.files.aggregate(pipeline).to_list(100)
            return {"upload_stats": results}

        except Exception as e:
            logger.error("Failed to get upload stats", extra={
                "days": days,
                "error": str(e)
            })
            raise DatabaseError("get_upload_stats", f"Upload stats retrieval failed: {str(e)}")

# Global database instance
file_db = FileDatabase()