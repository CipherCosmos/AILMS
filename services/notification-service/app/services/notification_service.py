"""
Notification Service Business Logic Layer
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import asyncio

from shared.common.logging import get_logger
from shared.common.errors import ValidationError, DatabaseError, NotFoundError

from database.database import notification_db
from models import (
    Notification, NotificationCreate, NotificationUpdate,
    NotificationTemplate, NotificationSettings,
    NotificationStats, NotificationType, NotificationPriority,
    NotificationStatus, NotificationChannel
)
from config.config import notification_service_settings

logger = get_logger("notification-service")

class NotificationService:
    """Notification service business logic"""

    def __init__(self):
        self.db = notification_db

    # Notification operations
    async def create_notification(self, notification_data: NotificationCreate) -> Notification:
        """Create a new notification"""
        try:
            # Validate notification data
            self._validate_notification_data(notification_data)

            notification_dict = notification_data.dict(by_alias=True)
            notification_dict["_id"] = self._generate_notification_id()
            notification_dict["status"] = NotificationStatus.PENDING
            notification_dict["created_at"] = datetime.now(timezone.utc)
            notification_dict["updated_at"] = datetime.now(timezone.utc)

            notification_id = await self.db.save_notification(notification_dict)

            # Get created notification
            created_notification = await self.db.get_notification(notification_id)
            if not created_notification:
                raise DatabaseError("create_notification", "Failed to retrieve created notification")

            # Send notification asynchronously
            asyncio.create_task(self._send_notification(created_notification))

            logger.info("Notification created", extra={
                "notification_id": notification_id,
                "recipient_id": notification_data.recipient_id,
                "type": notification_data.type.value
            })

            return Notification(**created_notification)

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to create notification", extra={"error": str(e)})
            raise DatabaseError("create_notification", f"Notification creation failed: {str(e)}")

    async def get_notification(self, notification_id: str) -> Notification:
        """Get notification by ID"""
        try:
            notification_data = await self.db.get_notification(notification_id)
            if not notification_data:
                raise NotFoundError("Notification", notification_id)

            return Notification(**notification_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get notification", extra={
                "notification_id": notification_id,
                "error": str(e)
            })
            raise DatabaseError("get_notification", f"Notification retrieval failed: {str(e)}")

    async def get_user_notifications(self, user_id: str, limit: int = 50,
                                   status: Optional[NotificationStatus] = None) -> List[Notification]:
        """Get notifications for a user"""
        try:
            notifications_data = await self.db.get_user_notifications(user_id, limit, status)
            return [Notification(**notification) for notification in notifications_data]

        except Exception as e:
            logger.error("Failed to get user notifications", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_user_notifications", f"User notifications retrieval failed: {str(e)}")

    async def update_notification(self, notification_id: str, updates: NotificationUpdate) -> Notification:
        """Update notification"""
        try:
            update_dict = updates.dict(exclude_unset=True)
            if not update_dict:
                raise ValidationError("No valid fields provided for update", "updates")

            update_dict["updated_at"] = datetime.now(timezone.utc)

            success = await self.db.update_notification(notification_id, update_dict)
            if not success:
                raise DatabaseError("update_notification", "Failed to update notification")

            # Get updated notification
            updated_notification = await self.get_notification(notification_id)

            logger.info("Notification updated", extra={
                "notification_id": notification_id,
                "updated_fields": list(update_dict.keys())
            })

            return updated_notification

        except (ValidationError, NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error("Failed to update notification", extra={
                "notification_id": notification_id,
                "error": str(e)
            })
            raise DatabaseError("update_notification", f"Notification update failed: {str(e)}")

    async def mark_as_read(self, notification_id: str, user_id: str) -> Notification:
        """Mark notification as read"""
        try:
            # Verify ownership
            notification = await self.get_notification(notification_id)
            if notification.recipient_id != user_id:
                raise ValidationError("Not authorized to update this notification", "notification_id")

            updates = NotificationUpdate(
                status=NotificationStatus.READ,
                read_at=datetime.now(timezone.utc)
            )

            return await self.update_notification(notification_id, updates)

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error("Failed to mark notification as read", extra={
                "notification_id": notification_id,
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("mark_as_read", f"Mark as read failed: {str(e)}")

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete notification"""
        try:
            # Verify ownership
            notification = await self.get_notification(notification_id)
            if notification.recipient_id != user_id:
                raise ValidationError("Not authorized to delete this notification", "notification_id")

            success = await self.db.delete_notification(notification_id)

            logger.info("Notification deleted", extra={
                "notification_id": notification_id,
                "user_id": user_id
            })

            return success

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error("Failed to delete notification", extra={
                "notification_id": notification_id,
                "error": str(e)
            })
            raise DatabaseError("delete_notification", f"Notification deletion failed: {str(e)}")

    # Bulk operations
    async def create_bulk_notifications(self, notifications: List[NotificationCreate]) -> List[str]:
        """Create multiple notifications"""
        try:
            notification_ids = []

            for notification_data in notifications:
                notification = await self.create_notification(notification_data)
                notification_ids.append(notification.id)

            logger.info("Bulk notifications created", extra={
                "count": len(notification_ids),
                "notification_ids": notification_ids[:5]  # Log first 5 IDs
            })

            return notification_ids

        except Exception as e:
            logger.error("Failed to create bulk notifications", extra={"error": str(e)})
            raise DatabaseError("create_bulk_notifications", f"Bulk notification creation failed: {str(e)}")

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all user's notifications as read"""
        try:
            count = await self.db.mark_all_as_read(user_id)

            logger.info("All notifications marked as read", extra={
                "user_id": user_id,
                "count": count
            })

            return count

        except Exception as e:
            logger.error("Failed to mark all notifications as read", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("mark_all_as_read", f"Mark all as read failed: {str(e)}")

    # Notification settings operations
    async def get_notification_settings(self, user_id: str) -> NotificationSettings:
        """Get user's notification settings"""
        try:
            settings_data = await self.db.get_notification_settings(user_id)
            if not settings_data:
                # Create default settings
                return await self._create_default_settings(user_id)

            return NotificationSettings(**settings_data)

        except Exception as e:
            logger.error("Failed to get notification settings", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_notification_settings", f"Notification settings retrieval failed: {str(e)}")

    async def update_notification_settings(self, user_id: str, settings: NotificationSettings) -> NotificationSettings:
        """Update user's notification settings"""
        try:
            settings_dict = settings.dict(exclude_unset=True)
            settings_dict["updated_at"] = datetime.now(timezone.utc)

            success = await self.db.update_notification_settings(user_id, settings_dict)
            if not success:
                raise DatabaseError("update_notification_settings", "Failed to update notification settings")

            # Get updated settings
            updated_settings = await self.get_notification_settings(user_id)

            logger.info("Notification settings updated", extra={
                "user_id": user_id,
                "updated_fields": list(settings_dict.keys())
            })

            return updated_settings

        except DatabaseError:
            raise
        except Exception as e:
            logger.error("Failed to update notification settings", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_notification_settings", f"Notification settings update failed: {str(e)}")

    # Analytics operations
    async def get_notification_stats(self, user_id: Optional[str] = None, period: str = "month") -> NotificationStats:
        """Get notification statistics"""
        try:
            stats_data = await self.db.get_notification_stats(user_id, period)
            return NotificationStats(**stats_data)

        except Exception as e:
            logger.error("Failed to get notification stats", extra={
                "user_id": user_id,
                "period": period,
                "error": str(e)
            })
            raise DatabaseError("get_notification_stats", f"Notification stats retrieval failed: {str(e)}")

    # Template operations
    async def get_notification_templates(self) -> List[NotificationTemplate]:
        """Get all notification templates"""
        try:
            templates_data = await self.db.get_notification_templates()
            return [NotificationTemplate(**template) for template in templates_data]

        except Exception as e:
            logger.error("Failed to get notification templates", extra={"error": str(e)})
            raise DatabaseError("get_notification_templates", f"Notification templates retrieval failed: {str(e)}")

    # Helper methods
    def _validate_notification_data(self, notification_data: NotificationCreate) -> None:
        """Validate notification data"""
        if len(notification_data.title) > notification_service_settings.max_title_length:
            raise ValidationError("Notification title too long", "title")

        if len(notification_data.message) > notification_service_settings.max_message_length:
            raise ValidationError("Notification message too long", "message")

        if not notification_data.channels:
            raise ValidationError("At least one delivery channel required", "channels")

    def _generate_notification_id(self) -> str:
        """Generate unique notification ID"""
        import uuid
        return f"notif_{uuid.uuid4().hex}"

    async def _create_default_settings(self, user_id: str) -> NotificationSettings:
        """Create default notification settings for user"""
        default_settings = {
            "user_id": user_id,
            "email_enabled": True,
            "in_app_enabled": True,
            "sms_enabled": False,
            "push_enabled": False,
            "course_updates": True,
            "assignment_deadlines": True,
            "grade_notifications": True,
            "achievement_notifications": True,
            "system_announcements": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        await self.db.save_notification_settings(default_settings)
        return NotificationSettings(**default_settings)

    async def _send_notification(self, notification: Dict[str, Any]) -> None:
        """Send notification through configured channels"""
        try:
            notification_id = notification["_id"]
            channels = notification.get("channels", [])

            # Update status to sent
            await self.db.update_notification(notification_id, {
                "status": NotificationStatus.SENT,
                "sent_at": datetime.now(timezone.utc)
            })

            # Send through each channel
            for channel in channels:
                try:
                    if channel == NotificationChannel.EMAIL:
                        await self._send_email_notification(notification)
                    elif channel == NotificationChannel.IN_APP:
                        await self._send_in_app_notification(notification)
                    elif channel == NotificationChannel.SMS:
                        await self._send_sms_notification(notification)
                    elif channel == NotificationChannel.PUSH:
                        await self._send_push_notification(notification)

                    # Update delivery status
                    await self.db.update_notification(notification_id, {
                        "status": NotificationStatus.DELIVERED,
                        "delivered_at": datetime.now(timezone.utc)
                    })

                except Exception as e:
                    logger.error(f"Failed to send notification via {channel}", extra={
                        "notification_id": notification_id,
                        "channel": channel,
                        "error": str(e)
                    })

        except Exception as e:
            logger.error("Failed to send notification", extra={
                "notification_id": notification["_id"],
                "error": str(e)
            })

    async def _send_email_notification(self, notification: Dict[str, Any]) -> None:
        """Send email notification"""
        # Implementation would integrate with email service
        logger.info("Email notification sent", extra={
            "notification_id": notification["_id"],
            "recipient_id": notification["recipient_id"]
        })

    async def _send_in_app_notification(self, notification: Dict[str, Any]) -> None:
        """Send in-app notification"""
        # Implementation would integrate with real-time messaging
        logger.info("In-app notification sent", extra={
            "notification_id": notification["_id"],
            "recipient_id": notification["recipient_id"]
        })

    async def _send_sms_notification(self, notification: Dict[str, Any]) -> None:
        """Send SMS notification"""
        # Implementation would integrate with SMS service
        logger.info("SMS notification sent", extra={
            "notification_id": notification["_id"],
            "recipient_id": notification["recipient_id"]
        })

    async def _send_push_notification(self, notification: Dict[str, Any]) -> None:
        """Send push notification"""
        # Implementation would integrate with push notification service
        logger.info("Push notification sent", extra={
            "notification_id": notification["_id"],
            "recipient_id": notification["recipient_id"]
        })

# Global service instance
notification_service = NotificationService()