# AI Service Routes Package
from .generation import router as generation_router
from .enhancement import router as enhancement_router
from .analysis import router as analysis_router
from .personalization import router as personalization_router
from .health import router as health_router

__all__ = [
    "generation_router",
    "enhancement_router",
    "analysis_router",
    "personalization_router",
    "health_router"
]