"""
Notification Service - FastAPI Application Factory
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
    notifications_router,
    websocket_router,
    health_router
)

# Initialize logger
logger = get_logger("notification-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting Notification Service", extra={
        "environment": settings.environment,
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
    logger.info("Shutting down Notification Service")
    await close_connection()
    await close_cache()

def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="LMS Notification Service",
        description="Real-time notifications and WebSocket communication service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Add middleware
    app.add_middleware(create_cors_middleware())
    app.add_middleware(RequestLoggingMiddleware)

    # Add rate limiting in production
    if settings.environment == "production":
        app.add_middleware(RateLimitMiddleware, requests_per_minute=500)

    # Include routers
    app.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
    app.include_router(websocket_router, prefix="", tags=["WebSocket"])
    app.include_router(health_router, prefix="", tags=["Health"])

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "service": "Notification Service",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "websocket": "/ws/{user_id}",
            "endpoints": {
                "create_notification": "/notifications",
                "get_notifications": "/notifications",
                "mark_as_read": "/notifications/{id}/read"
            }
        }

    return app

# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8007,
        reload=settings.environment == "development",
        log_level="info"
    )