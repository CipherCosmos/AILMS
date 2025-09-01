# Auth Service Routes Package
from .auth import router as auth_router
from .users import router as users_router
from .tokens import router as tokens_router
from .health import router as health_router

__all__ = [
    "auth_router",
    "users_router",
    "tokens_router",
    "health_router"
]