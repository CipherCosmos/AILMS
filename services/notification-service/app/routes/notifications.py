"""
Notification management routes for Notification Service
"""
from fastapi import APIRouter, Depends
from typing import Optional

from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

from utils.notification_utils import get_current_user, require_role
from services.notification_service import notification_service
from models import (
    NotificationCreate, Notification, NotificationStats
)

logger = get_logger("notification-service")
router = APIRouter()

@router.post("/", response_model=dict)
async def create_notification(
    notification_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new notification.

    - **user_id**: ID of the user to notify
    - **title**: Notification title
    - **message**: Notification message
    - **type**: Notification type (system, course, assignment, etc.)
    """
    try:
        # Check permissions (only admins/instructors can send notifications to others)
        user_id = notification_data.get("user_id")
        if user_id != current_user["id"] and current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to send notifications to other users")

        # Create notification using service layer
        create_data = NotificationCreate(
            recipient_id=user_id,
            title=notification_data.get("title", ""),
            message=notification_data.get("message", ""),
            type=notification_data.get("type", "system"),
            sender_id=current_user["id"],
            course_id=notification_data.get("course_id"),
            assignment_id=notification_data.get("assignment_id"),
            priority=notification_data.get("priority", "medium")
        )

        notification = await notification_service.create_notification(create_data)

        logger.info("Notification created", extra={
            "notification_id": notification.id,
            "user_id": user_id,
            "type": notification_data.get("type", "system"),
            "created_by": current_user["id"]
        })

        return {
            "status": "created",
            "notification_id": notification.id,
            "message": "Notification created successfully"
        }

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create notification", extra={
            "user_id": notification_data.get("user_id"),
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to create notification")

@router.get("/")
async def get_notifications(
    limit: int = 50,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's notifications.

    - **limit**: Maximum number of notifications to return
    - **unread_only**: Return only unread notifications
    """
    try:
        # Use service layer
        from models import NotificationStatus
        status = NotificationStatus.READ if not unread_only else None
        notifications = await notification_service.get_user_notifications(
            current_user["id"],
            limit=limit,
            status=status
        )

        logger.info("Notifications retrieved", extra={
            "user_id": current_user["id"],
            "count": len(notifications),
            "unread_only": unread_only
        })

        return {
            "notifications": [notification.dict() for notification in notifications],
            "total": len(notifications),
            "limit": limit,
            "unread_only": unread_only
        }

    except Exception as e:
        logger.error("Failed to get notifications", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve notifications")

@router.get("/{notification_id}", response_model=Notification)
async def get_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific notification.

    - **notification_id**: Notification identifier
    """
    try:
        # Use service layer
        notification = await notification_service.get_notification(notification_id)

        # Verify ownership
        if notification.recipient_id != current_user["id"]:
            raise AuthorizationError("Not authorized to view this notification")

        logger.info("Notification retrieved", extra={
            "notification_id": notification_id,
            "user_id": current_user["id"]
        })

        return notification

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get notification", extra={
            "notification_id": notification_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve notification")

@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark notification as read.

    - **notification_id**: Notification identifier
    """
    try:
        # Use service layer
        notification = await notification_service.mark_as_read(notification_id, current_user["id"])

        logger.info("Notification marked as read", extra={
            "notification_id": notification_id,
            "user_id": current_user["id"]
        })

        return {"status": "marked_as_read"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to mark notification as read", extra={
            "notification_id": notification_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to mark notification as read")

@router.put("/mark-all-read")
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    """
    Mark all user's notifications as read.
    """
    try:
        # Use service layer
        marked_count = await notification_service.mark_all_as_read(current_user["id"])

        logger.info("All notifications marked as read", extra={
            "user_id": current_user["id"],
            "marked_count": marked_count
        })

        return {
            "status": "marked_all_as_read",
            "marked_count": marked_count
        }

    except Exception as e:
        logger.error("Failed to mark all notifications as read", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to mark notifications as read")

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a notification.

    - **notification_id**: Notification identifier
    """
    try:
        # Use service layer
        success = await notification_service.delete_notification(notification_id, current_user["id"])

        if not success:
            raise NotFoundError("Notification", notification_id)

        logger.info("Notification deleted", extra={
            "notification_id": notification_id,
            "user_id": current_user["id"]
        })

        return {"status": "deleted"}

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to delete notification", extra={
            "notification_id": notification_id,
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to delete notification")

@router.get("/stats/summary", response_model=NotificationStats)
async def get_notification_stats(current_user: dict = Depends(get_current_user)):
    """
    Get notification statistics for the current user.
    """
    try:
        # Use service layer
        stats = await notification_service.get_notification_stats(current_user["id"])

        logger.info("Notification stats retrieved", extra={
            "user_id": current_user["id"],
            "total_sent": stats.total_sent,
            "total_read": stats.total_read
        })

        return stats

    except Exception as e:
        logger.error("Failed to get notification stats", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        from fastapi import HTTPException
        raise HTTPException(500, "Failed to retrieve notification statistics")