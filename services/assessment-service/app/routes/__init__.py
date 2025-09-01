# Assessment Service Routes Package
from .assignments import router as assignments_router
from .submissions import router as submissions_router
from .grading import router as grading_router
from .health import router as health_router

__all__ = [
    "assignments_router",
    "submissions_router",
    "grading_router",
    "health_router"
]