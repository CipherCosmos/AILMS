from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import get_database
from auth import _current_user
from models import Notification
from datetime import datetime

notifications_router = APIRouter()

@notifications_router.get("")
async def get_notifications(user=Depends(_current_user)):
    """Get user's notifications"""
    db = get_database()
    notifications = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).to_list(50)
    return [Notification(**n) for n in notifications]

@notifications_router.post("/{nid}/read")
async def mark_notification_read(nid: str, user=Depends(_current_user)):
    """Mark notification as read"""
    db = get_database()
    notification = await db.notifications.find_one({"_id": nid, "user_id": user["id"]})
    if not notification:
        raise HTTPException(404, "Notification not found")

    await db.notifications.update_one({"_id": nid}, {"$set": {"read": True}})
    return {"status": "marked_read"}

@notifications_router.post("/send/{user_id}")
async def send_notification(user_id: str, notification_data: dict, sender=Depends(_current_user)):
    """Send notification to user (admin/instructor only)"""
    if sender["role"] not in ["admin", "instructor"]:
        raise HTTPException(403, "Not authorized to send notifications")

    db = get_database()

    # Verify target user exists
    target_user = await db.users.find_one({"_id": user_id})
    if not target_user:
        raise HTTPException(404, "User not found")

    notification = Notification(
        user_id=user_id,
        title=notification_data.get("title", ""),
        message=notification_data.get("message", ""),
        type=notification_data.get("type", "general")
    )

    doc = notification.dict()
    doc["_id"] = notification.id
    await db.notifications.insert_one(doc)

    return {"status": "sent", "notification_id": notification.id}

@notifications_router.delete("/{nid}")
async def delete_notification(nid: str, user=Depends(_current_user)):
    """Delete notification"""
    db = get_database()
    result = await db.notifications.delete_one({"_id": nid, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Notification not found")
    return {"status": "deleted"}