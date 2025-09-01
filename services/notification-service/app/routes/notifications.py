"""
Notification management routes for Notification Service
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from shared.common.auth import get_current_user, require_admin
from shared.common.database import DatabaseOperations
from shared.common.errors import ValidationError, NotFoundError, AuthorizationError
from shared.common.logging import get_logger

logger = get_logger("notification-service")
router = APIRouter()
notifications_db = DatabaseOperations("notifications")

@router.post("/")
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
        user_id = notification_data.get("user_id")
        title = notification_data.get("title")
        message = notification_data.get("message")
        notification_type = notification_data.get("type", "system")

        if not user_id:
            raise ValidationError("User ID is required", "user_id")
        if not title:
            raise ValidationError("Title is required", "title")
        if not message:
            raise ValidationError("Message is required", "message")

        # Check permissions (only admins/instructors can send notifications to others)
        if user_id != current_user["id"] and current_user["role"] not in ["admin", "instructor"]:
            raise AuthorizationError("Not authorized to send notifications to other users")

        from shared.database.database import _uuid
        notification = {
            "_id": _uuid(),
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "read": False,
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc)
        }

        await notifications_db.insert_one(notification)

        logger.info("Notification created", extra={
            "notification_id": notification["_id"],
            "user_id": user_id,
            "type": notification_type,
            "created_by": current_user["id"]
        })

        # TODO: Send real-time notification via WebSocket
        # await send_websocket_notification(user_id, notification)

        return {
            "status": "created",
            "notification_id": notification["_id"],
            "message": "Notification created successfully"
        }

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create notification", extra={
            "user_id": notification_data.get("user_id"),
            "error": str(e)
        })
        raise HTTPException(500, "Failed to create notification")

@router.get("/")
async def get_notifications(
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's notifications.

    - **limit**: Maximum number of notifications to return
    - **offset**: Number of notifications to skip
    - **unread_only**: Return only unread notifications
    """
    try:
        # Build query
        query = {"user_id": current_user["id"]}
        if unread_only:
            query["read"] = False

        # Get notifications
        notifications = await notifications_db.find_many(
            query,
            sort=[("created_at", -1)],
            limit=limit,
            skip=offset
        )

        # Get total count
        total_count = len(await notifications_db.find_many(query))

        return {
            "notifications": notifications,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "unread_only": unread_only
        }

    except Exception as e:
        logger.error("Failed to get notifications", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve notifications")

@router.get("/{notification_id}")
async def get_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific notification.

    - **notification_id**: Notification identifier
    """
    try:
        notification = await notifications_db.find_one({
            "_id": notification_id,
            "user_id": current_user["id"]
        })

        if not notification:
            raise NotFoundError("Notification", notification_id)

        return notification

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get notification", extra={
            "notification_id": notification_id,
            "error": str(e)
        })
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
        # Update notification
        result = await notifications_db.update_one(
            {"_id": notification_id, "user_id": current_user["id"]},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}}
        )

        if not result:
            # Check if notification exists
            notification = await notifications_db.find_one({
                "_id": notification_id,
                "user_id": current_user["id"]
            })
            if not notification:
                raise NotFoundError("Notification", notification_id)
            # Already read
            return {"status": "already_read"}

        logger.info("Notification marked as read", extra={
            "notification_id": notification_id,
            "user_id": current_user["id"]
        })

        return {"status": "marked_as_read"}

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to mark notification as read", extra={
            "notification_id": notification_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to mark notification as read")

@router.put("/mark-all-read")
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    """
    Mark all user's notifications as read.
    """
    try:
        # Update all unread notifications
        unread_notifications = await notifications_db.find_many({
            "user_id": current_user["id"],
            "read": False
        })
        marked_count = 0
        for notification in unread_notifications:
            await notifications_db.update_one(
                {"_id": notification["_id"]},
                {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}}
            )
            marked_count += 1

        logger.info("All notifications marked as read", extra={
            "user_id": current_user["id"],
            "marked_count": result.modified_count
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
        # Delete notification
        result = await notifications_db.delete_one({
            "_id": notification_id,
            "user_id": current_user["id"]
        })

        if not result:
            raise NotFoundError("Notification", notification_id)

        logger.info("Notification deleted", extra={
            "notification_id": notification_id,
            "user_id": current_user["id"]
        })

        return {"status": "deleted"}

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to delete notification", extra={
            "notification_id": notification_id,
            "error": str(e)
        })
        raise HTTPException(500, "Failed to delete notification")

@router.get("/stats/summary")
async def get_notification_stats(current_user: dict = Depends(get_current_user)):
    """
    Get notification statistics for the current user.
    """
    try:
        # Get counts
        total_count = len(await notifications_db.find_many({"user_id": current_user["id"]}))
        unread_count = len(await notifications_db.find_many({
            "user_id": current_user["id"],
            "read": False
        }))

        # Get recent notifications (last 7 days)
        seven_days_ago = datetime.now(timezone.utc).timestamp() - (7 * 24 * 60 * 60)
        recent_count = len(await notifications_db.find_many({
            "user_id": current_user["id"],
            "created_at": {"$gte": datetime.fromtimestamp(seven_days_ago, timezone.utc)}
        }))

        return {
            "total_notifications": total_count,
            "unread_notifications": unread_count,
            "recent_notifications": recent_count,
            "read_percentage": round(((total_count - unread_count) / max(total_count, 1)) * 100, 1)
        }

    except Exception as e:
        logger.error("Failed to get notification stats", extra={
            "user_id": current_user["id"],
            "error": str(e)
        })
        raise HTTPException(500, "Failed to retrieve notification statistics")