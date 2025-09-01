"""
API Gateway - FastAPI Application Factory
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
    proxy_router,
    health_router,
    discovery_router,
    monitoring_router
)

# Initialize logger
logger = get_logger("api-gateway")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting API Gateway", extra={
        "environment": settings.environment,
        "services_count": 8,  # Number of microservices
        "version": "1.0.0"
    })

    # Test database connection (for gateway-specific data if needed)
    try:
        db = await get_database()
        await db.command('ping')
        logger.info("Database connection established")
    except Exception as e:
        logger.warning("Database connection failed", extra={"error": str(e)})

    yield

    # Shutdown
    logger.info("Shutting down API Gateway")
    await close_connection()
    await close_cache()

def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="LMS API Gateway",
        description="Central entry point for LMS microservices architecture",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Add middleware
    app.add_middleware(create_cors_middleware())
    app.add_middleware(RequestLoggingMiddleware)

    # Add rate limiting in production (moderate for gateway)
    if settings.environment == "production":
        app.add_middleware(RateLimitMiddleware, requests_per_minute=1000)

    # Include routers
    app.include_router(proxy_router, prefix="", tags=["Proxy"])
    app.include_router(health_router, prefix="", tags=["Health"])
    app.include_router(discovery_router, prefix="/discovery", tags=["Service Discovery"])
    app.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with gateway information"""
        return {
            "service": "API Gateway",
            "version": "1.0.0",
            "status": "running",
            "description": "Central entry point for LMS microservices",
            "services": {
                "auth": "http://auth-service:8001",
                "course": "http://course-service:8002",
                "user": "http://user-service:8003",
                "ai": "http://ai-service:8004",
                "assessment": "http://assessment-service:8005",
                "analytics": "http://analytics-service:8006",
                "notification": "http://notification-service:8007",
                "file": "http://file-service:8008"
            },
            "docs": "/docs",
            "health": "/health",
            "service_health": "/health/services",
            "monitoring": "/monitoring"
        }

    # API root endpoint
    @app.get("/api/")
    async def api_root():
        """API root endpoint"""
        return {
            "message": "LMS API Gateway",
            "version": "1.0.0",
            "endpoints": {
                "auth": "/auth",
                "courses": "/courses",
                "users": "/users",
                "ai": "/ai",
                "assignments": "/assignments",
                "analytics": "/analytics",
                "notifications": "/notifications",
                "files": "/files"
            },
            "health": "/health/services",
            "monitoring": "/monitoring/metrics"
        }

    return app

# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level="info"
    )