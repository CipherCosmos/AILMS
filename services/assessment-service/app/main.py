"""
Assessment Service - FastAPI Application Factory
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.database import get_database, close_connection
from shared.common.cache import close_connection as close_cache
# Temporarily disabled middleware imports due to FastAPI version compatibility issues
# from shared.common.middleware import (
#     create_cors_middleware,
#     RequestLoggingMiddleware,
#     RateLimitMiddleware
# )

from routes.assignments import router as assignments_router
from routes.submissions import router as submissions_router
from routes.grading import router as grading_router
from routes.health import router as health_router

# Initialize logger
logger = get_logger("assessment-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting Assessment Service", extra={
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
    logger.info("Shutting down Assessment Service")
    await close_connection()
    await close_cache()

def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="LMS Assessment Service",
        description="Assignment management, submission handling, and grading service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Temporarily disabled middleware due to import issues
    # app.add_middleware(create_cors_middleware())
    # app.add_middleware(RequestLoggingMiddleware)

    # Add rate limiting in production
    # if settings.environment == "production":
    #     app.add_middleware(RateLimitMiddleware, requests_per_minute=200)

    # Include routers
    app.include_router(assignments_router, prefix="/assignments", tags=["Assignments"])
    app.include_router(submissions_router, prefix="/submissions", tags=["Submissions"])
    app.include_router(grading_router, prefix="/grading", tags=["Grading"])
    app.include_router(health_router, prefix="", tags=["Health"])

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "service": "Assessment Service",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "assignments": "/assignments",
                "submissions": "/submissions",
                "grading": "/grading"
            }
        }

    return app

# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8005,
        reload=settings.environment == "development",
        log_level="info"
    )