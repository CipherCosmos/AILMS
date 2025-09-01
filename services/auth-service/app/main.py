"""
Auth Service - FastAPI Application Factory
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.database import get_database, close_connection
from shared.common.cache import close_connection as close_cache
from shared.common.middleware import (
    create_cors_middleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware
)

from .routes import (
    auth_router,
    users_router,
    tokens_router,
    health_router
)

# Initialize logger
logger = get_logger("auth-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting Auth Service", extra={
        "environment": settings.environment,
        "jwt_expiry_access": f"{settings.access_expire_min} minutes",
        "jwt_expiry_refresh": f"{settings.refresh_expire_days} days",
        "database": settings.db_name
    })

    # Test database connection
    try:
        db = await get_database()
        await db.command('ping')
        logger.info("Database connection established")
    except Exception as e:
        logger.error("Database connection failed", extra={"error": str(e)})
        raise

    yield

    # Shutdown
    logger.info("Shutting down Auth Service")
    await close_connection()
    await close_cache()

def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="LMS Auth Service",
        description="User authentication and authorization service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Add middleware
    app.add_middleware(create_cors_middleware())
    app.add_middleware(RequestLoggingMiddleware)

    # Add rate limiting in production (strict for auth operations)
    if settings.environment == "production":
        app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

    # Include routers
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(users_router, prefix="/auth", tags=["User Management"])
    app.include_router(tokens_router, prefix="/auth", tags=["Token Management"])
    app.include_router(health_router, prefix="", tags=["Health"])

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "service": "Auth Service",
            "version": "1.0.0",
            "status": "running",
            "description": "User authentication and authorization",
            "endpoints": {
                "register": "/auth/register",
                "login": "/auth/login",
                "refresh": "/auth/refresh",
                "me": "/auth/me",
                "users": "/auth/users",
                "health": "/health"
            },
            "docs": "/docs",
            "security": {
                "jwt_access_expiry": f"{settings.access_expire_min} minutes",
                "jwt_refresh_expiry": f"{settings.refresh_expire_days} days"
            }
        }

    return app

# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.environment == "development",
        log_level="info"
    )