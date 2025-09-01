# Course Service Routes Package
from .courses import router as courses_router
from .lessons import router as lessons_router
from .progress import router as progress_router
from .ai import router as ai_router
from .health import router as health_router

__all__ = [
    "courses_router",
    "lessons_router",
    "progress_router",
    "ai_router",
    "health_router"
]