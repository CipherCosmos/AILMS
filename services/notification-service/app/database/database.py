"""
Notification Service Database Operations
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.errors import DatabaseError

logger = get_logger("notification-service-db")

class NotificationDatabase:
    """Notification service database operations"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self._initialized = False

    async def init_db(self):
        """Initialize database connection"""
        if self._initialized:
            return

        try:
            self.client = AsyncIOMotorClient(settings.mongo_url)
            self.db = self.client[settings.db_name]
            await self._create_indexes()
            self._initialized = True
            logger.info("Notification database initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize notification database", extra={"error": str(e)})
            raise DatabaseError("init_db", f"Database initialization failed: {str(e)}")

    async def close_db(self):
        """Close database connection"""
        if self.client:
            self.client.close()
        self._initialized = False
        logger.info("Notification database connection closed")

    async def _create_indexes(self):
        """Create necessary database indexes"""
        try:
            # Notifications indexes
            await self.db.notifications.create_index("recipient_id")
            await self.db.notifications.create_index("status")
            await self.db.notifications.create_index("type")
            await self.db.notifications.create_index("created_at")
            await self.db.notifications.create_index([("recipient_id", 1), ("created_at", -1)])

            # Notification settings indexes
            await self.db.notification_settings.create_index("user_id", unique=True)

            # Notification templates indexes
            await self.db.notification_templates.create_index("type", unique=True)
            await self.db.notification_templates.create_index("name")

            logger.info("Notification database indexes created successfully")
        except Exception as e:
            logger.error("Failed to create notification database indexes", extra={"error": str(e)})

    # Notification operations
    async def save_notification(self, notification_data: Dict[str, Any]) -> str:
        """Save notification to database"""
        try:
            result = await self.db.notifications.insert_one(notification_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error("Failed to save notification", extra={"error": str(e)})
            raise DatabaseError("save_notification", f"Notification save failed: {str(e)}")

    async def get_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Get notification by ID"""
        try:
            return await self.db.notifications.find_one({"_id": notification_id})
        except Exception as e:
            logger.error("Failed to get notification", extra={
                "notification_id": notification_id,
                "error": str(e)
            })
            raise DatabaseError("get_notification", f"Notification retrieval failed: {str(e)}")

    async def get_user_notifications(self, user_id: str, limit: int = 50,
                                   status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        try:
            query = {"recipient_id": user_id}
            if status:
                query["status"] = status

            notifications = await self.db.notifications.find(query).sort("created_at", -1).limit(limit).to_list(limit)
            return notifications
        except Exception as e:
            logger.error("Failed to get user notifications", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_user_notifications", f"User notifications retrieval failed: {str(e)}")

    async def update_notification(self, notification_id: str, updates: Dict[str, Any]) -> bool:
        """Update notification"""
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.notifications.update_one(
                {"_id": notification_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error("Failed to update notification", extra={
                "notification_id": notification_id,
                "error": str(e)
            })
            raise DatabaseError("update_notification", f"Notification update failed: {str(e)}")

    async def delete_notification(self, notification_id: str) -> bool:
        """Delete notification"""
        try:
            result = await self.db.notifications.delete_one({"_id": notification_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error("Failed to delete notification", extra={
                "notification_id": notification_id,
                "error": str(e)
            })
            raise DatabaseError("delete_notification", f"Notification deletion failed: {str(e)}")

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all user's notifications as read"""
        try:
            result = await self.db.notifications.update_many(
                {"recipient_id": user_id, "status": {"$ne": "read"}},
                {
                    "$set": {
                        "status": "read",
                        "read_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count
        except Exception as e:
            logger.error("Failed to mark all notifications as read", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("mark_all_as_read", f"Mark all as read failed: {str(e)}")

    # Notification settings operations
    async def get_notification_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's notification settings"""
        try:
            return await self.db.notification_settings.find_one({"user_id": user_id})
        except Exception as e:
            logger.error("Failed to get notification settings", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_notification_settings", f"Notification settings retrieval failed: {str(e)}")

    async def save_notification_settings(self, settings_data: Dict[str, Any]) -> str:
        """Save notification settings"""
        try:
            result = await self.db.notification_settings.insert_one(settings_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error("Failed to save notification settings", extra={"error": str(e)})
            raise DatabaseError("save_notification_settings", f"Notification settings save failed: {str(e)}")

    async def update_notification_settings(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update notification settings"""
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            result = await self.db.notification_settings.update_one(
                {"user_id": user_id},
                {"$set": updates},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error("Failed to update notification settings", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_notification_settings", f"Notification settings update failed: {str(e)}")

    # Analytics operations
    async def get_notification_stats(self, user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get notification statistics"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Build query
            query = {"created_at": {"$gte": start_date}}
            if user_id:
                query["recipient_id"] = user_id

            # Get statistics
            total_sent = await self.db.notifications.count_documents(query)

            delivered_query = query.copy()
            delivered_query["status"] = "delivered"
            total_delivered = await self.db.notifications.count_documents(delivered_query)

            read_query = query.copy()
            read_query["status"] = "read"
            total_read = await self.db.notifications.count_documents(read_query)

            # Calculate rates
            delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0.0
            read_rate = (total_read / total_sent * 100) if total_sent > 0 else 0.0

            return {
                "total_sent": total_sent,
                "total_delivered": total_delivered,
                "total_read": total_read,
                "delivery_rate": round(delivery_rate, 2),
                "read_rate": round(read_rate, 2),
                "period": f"{days} days"
            }

        except Exception as e:
            logger.error("Failed to get notification stats", extra={
                "user_id": user_id,
                "days": days,
                "error": str(e)
            })
            raise DatabaseError("get_notification_stats", f"Notification stats retrieval failed: {str(e)}")

    # Template operations
    async def get_notification_templates(self) -> List[Dict[str, Any]]:
        """Get all notification templates"""
        try:
            templates = await self.db.notification_templates.find().to_list(100)
            return templates
        except Exception as e:
            logger.error("Failed to get notification templates", extra={"error": str(e)})
            raise DatabaseError("get_notification_templates", f"Notification templates retrieval failed: {str(e)}")

# Global database instance
notification_db = NotificationDatabase()