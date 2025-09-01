# User Service Routes Package
from .profiles import router as profiles_router
from .career import router as career_router
from .analytics import router as analytics_router
from .achievements import router as achievements_router
from .health import router as health_router

__all__ = [
    "profiles_router",
    "career_router",
    "analytics_router",
    "achievements_router",
    "health_router"
]