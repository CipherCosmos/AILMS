"""
Notification Service - Handles real-time notifications and WebSocket connections
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict
from datetime import datetime, timezone
import sys
import os
import json

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.config.config import settings
from shared.database.database import get_database, _uuid

app = FastAPI(title='Notification Service', version='1.0.0')

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

# JWT token validation for service-to-service calls
async def _current_user(token: Optional[str] = None):
    """Validate JWT token for service-to-service calls"""
    if not token:
        raise HTTPException(401, "No authentication token provided")

    try:
        import jwt
        from shared.config.config import settings

        # Decode and validate JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        # Verify token hasn't expired
        from datetime import datetime, timezone
        if payload.get("exp") and datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token has expired")

        # Get user from database to ensure they still exist
        db = get_database()
        user = await db.users.find_one({"_id": payload.get("sub")})
        if not user:
            raise HTTPException(401, "User not found")

        return {
            "id": user["_id"],
            "role": user.get("role", "student"),
            "email": user.get("email", ""),
            "name": user.get("name", "")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {str(e)}")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time notifications"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now
            await manager.send_personal_message(f"Echo: {data}", user_id)
    except WebSocketDisconnect:
        manager.disconnect(user_id)

@app.post("/notifications")
async def create_notification(notification_data: dict, user=Depends(_current_user)):
    """Create a new notification"""
    db = get_database()
    notification = {
        "_id": _uuid(),
        "user_id": notification_data.get("user_id"),
        "title": notification_data.get("title"),
        "message": notification_data.get("message"),
        "type": notification_data.get("type", "system"),
        "read": False,
        "created_at": datetime.now(timezone.utc)
    }

    await db.notifications.insert_one(notification)

    # Send real-time notification if user is connected
    await manager.send_personal_message(
        json.dumps({
            "type": "notification",
            "title": notification["title"],
            "message": notification["message"]
        }),
        notification["user_id"]
    )

    return {"status": "created", "notification_id": notification["_id"]}

@app.get("/notifications")
async def get_notifications(user=Depends(_current_user)):
    """Get user's notifications"""
    db = get_database()
    notifications = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).to_list(50)
    return notifications

@app.put("/notifications/{notification_id}/read")
async def mark_as_read(notification_id: str, user=Depends(_current_user)):
    """Mark notification as read"""
    db = get_database()
    await db.notifications.update_one(
        {"_id": notification_id, "user_id": user["id"]},
        {"$set": {"read": True}}
    )
    return {"status": "marked_as_read"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "notification"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Notification Service", "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8007, reload=settings.environment == 'development')