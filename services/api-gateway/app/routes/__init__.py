# API Gateway Routes Package
from .proxy import router as proxy_router
from .health import router as health_router
from .discovery import router as discovery_router
from .monitoring import router as monitoring_router

__all__ = [
    "proxy_router",
    "health_router",
    "discovery_router",
    "monitoring_router"
]