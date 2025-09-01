# Notification Service Routes Package
from .notifications import router as notifications_router
from .websocket import router as websocket_router
from .health import router as health_router

__all__ = [
    "notifications_router",
    "websocket_router",
    "health_router"
]