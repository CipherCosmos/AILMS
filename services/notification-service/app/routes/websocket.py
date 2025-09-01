"""
WebSocket routes for Notification Service
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json

from shared.common.logging import get_logger

logger = get_logger("notification-service")
router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info("WebSocket connection established", extra={
            "user_id": user_id,
            "total_connections": len(self.active_connections)
        })

    def disconnect(self, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info("WebSocket connection closed", extra={
                "user_id": user_id,
                "remaining_connections": len(self.active_connections)
            })

    async def send_personal_message(self, message: str, user_id: str):
        """Send a message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
                logger.debug("WebSocket message sent", extra={
                    "user_id": user_id,
                    "message_type": "personal"
                })
            except Exception as e:
                logger.error("Failed to send WebSocket message", extra={
                    "user_id": user_id,
                    "error": str(e)
                })
                # Remove broken connection
                self.disconnect(user_id)

    async def broadcast(self, message: str):
        """Send a message to all connected users"""
        disconnected_users = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error("Failed to broadcast to user", extra={
                    "user_id": user_id,
                    "error": str(e)
                })
                disconnected_users.append(user_id)

        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)

        logger.info("WebSocket broadcast completed", extra={
            "message": message[:100] + "..." if len(message) > 100 else message,
            "disconnected_users": len(disconnected_users)
        })

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected"""
        return user_id in self.active_connections

# Global connection manager instance
manager = ConnectionManager()

@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time notifications.

    - **user_id**: User identifier for the WebSocket connection
    """
    await manager.connect(websocket, user_id)

    try:
        # Send welcome message
        welcome_message = json.dumps({
            "type": "connection",
            "message": "Connected to notification service",
            "user_id": user_id,
            "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow()
        })
        await manager.send_personal_message(welcome_message, user_id)

        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()

                # Parse the message
                try:
                    message_data = json.loads(data)
                    message_type = message_data.get("type", "unknown")
                except json.JSONDecodeError:
                    message_type = "text"

                logger.debug("WebSocket message received", extra={
                    "user_id": user_id,
                    "message_type": message_type,
                    "data_length": len(data)
                })

                # Handle different message types
                if message_type == "ping":
                    # Respond to ping with pong
                    pong_message = json.dumps({
                        "type": "pong",
                        "timestamp": "2024-01-01T00:00:00Z"
                    })
                    await manager.send_personal_message(pong_message, user_id)

                elif message_type == "echo":
                    # Echo back the message
                    echo_message = json.dumps({
                        "type": "echo",
                        "original_message": message_data.get("message", data),
                        "timestamp": "2024-01-01T00:00:00Z"
                    })
                    await manager.send_personal_message(echo_message, user_id)

                else:
                    # For unknown message types, just acknowledge
                    ack_message = json.dumps({
                        "type": "acknowledged",
                        "received_type": message_type,
                        "timestamp": "2024-01-01T00:00:00Z"
                    })
                    await manager.send_personal_message(ack_message, user_id)

            except json.JSONDecodeError:
                # Handle non-JSON messages
                logger.warning("Received non-JSON message", extra={
                    "user_id": user_id,
                    "data": data[:100] + "..." if len(data) > 100 else data
                })

                # Echo back as text
                await manager.send_personal_message(f"Echo: {data}", user_id)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", extra={"user_id": user_id})
        manager.disconnect(user_id)

    except Exception as e:
        logger.error("WebSocket error", extra={
            "user_id": user_id,
            "error": str(e)
        })
        manager.disconnect(user_id)

@router.get("/ws/connections")
async def get_connection_stats():
    """
    Get WebSocket connection statistics (for monitoring).
    """
    return {
        "active_connections": manager.get_connection_count(),
        "status": "operational"
    }

@router.get("/ws/test/{user_id}")
async def test_websocket_connection(user_id: str):
    """
    Test endpoint to check if a user is connected via WebSocket.
    """
    is_connected = manager.is_user_connected(user_id)

    return {
        "user_id": user_id,
        "websocket_connected": is_connected,
        "message": "User is connected" if is_connected else "User is not connected"
    }

# Utility functions for other services to use
async def send_notification_to_user(user_id: str, notification: dict):
    """
    Send a notification to a specific user via WebSocket.
    This function can be imported and used by other services.
    """
    if manager.is_user_connected(user_id):
        message = json.dumps({
            "type": "notification",
            "notification": notification,
            "timestamp": "2024-01-01T00:00:00Z"
        })
        await manager.send_personal_message(message, user_id)
        return True
    return False

async def broadcast_notification(notification: dict, exclude_user_ids: list = None):
    """
    Broadcast a notification to all connected users.
    """
    if exclude_user_ids is None:
        exclude_user_ids = []

    message = json.dumps({
        "type": "broadcast",
        "notification": notification,
        "timestamp": "2024-01-01T00:00:00Z"
    })

    await manager.broadcast(message)

    logger.info("Notification broadcast", extra={
        "excluded_users": len(exclude_user_ids) if exclude_user_ids else 0
    })

# Export functions for use by other modules
__all__ = [
    "send_notification_to_user",
    "broadcast_notification",
    "manager"
]