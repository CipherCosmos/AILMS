# Analytics Service Routes Package
from .courses import router as courses_router
from .students import router as students_router
from .reports import router as reports_router
from .health import router as health_router

__all__ = [
    "courses_router",
    "students_router",
    "reports_router",
    "health_router"
]