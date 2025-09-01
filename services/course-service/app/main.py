"""
Course Service - FastAPI Application Factory
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

from routes.courses import router as courses_router
from routes.lessons import router as lessons_router
from routes.progress import router as progress_router
from routes.ai import router as ai_router
from routes.health import router as health_router

# Initialize logger
logger = get_logger("course-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting Course Service", extra={
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
    logger.info("Shutting down Course Service")
    await close_connection()
    await close_cache()

def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="LMS Course Service",
        description="Course management and AI-powered content generation service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Temporarily disabled middleware due to import issues
    # app.add_middleware(create_cors_middleware())
    # app.add_middleware(RequestLoggingMiddleware)

    # Add rate limiting in production (moderate for course operations)
    # if settings.environment == "production":
    #     app.add_middleware(RateLimitMiddleware, requests_per_minute=200)

    # Include routers
    app.include_router(courses_router, prefix="/courses", tags=["Course Management"])
    app.include_router(lessons_router, prefix="/courses", tags=["Lesson Management"])
    app.include_router(progress_router, prefix="/courses", tags=["Progress Tracking"])
    app.include_router(ai_router, prefix="/courses", tags=["AI Course Generation"])
    app.include_router(health_router, prefix="", tags=["Health"])

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "service": "Course Service",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "list_courses": "/courses",
                "create_course": "/courses",
                "get_course": "/courses/{id}",
                "update_course": "/courses/{id}",
                "enroll_course": "/courses/{id}/enroll",
                "add_lesson": "/courses/{id}/lessons",
                "update_progress": "/courses/{id}/progress",
                "ai_generate": "/courses/ai/generate_course"
            }
        }

    return app

# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.environment == "development",
        log_level="info"
    )