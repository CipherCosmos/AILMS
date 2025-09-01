# File Service Routes Package
from .files import router as files_router
from .upload import router as upload_router
from .health import router as health_router

__all__ = [
    "files_router",
    "upload_router",
    "health_router"
]