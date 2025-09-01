"""
User Service - FastAPI Application Factory
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from shared.config.config import settings
from shared.common.logging import get_logger
from shared.common.database import get_database, close_connection
from shared.common.cache import close_connection as close_cache
# from .middleware.auth_middleware import RequestLoggingMiddleware

from .routes.profiles import router as profiles_router
from .routes.career import router as career_router
from .routes.analytics import router as analytics_router
from .routes.achievements import router as achievements_router
from .routes.health import router as health_router

# Initialize logger
logger = get_logger("user-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting User Service", extra={
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
    logger.info("Shutting down User Service")
    await close_connection()
    await close_cache()

def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="LMS User Service",
        description="User profiles, career development, and learning analytics service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on your needs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware (commented out for now)
    # app.add_middleware(RequestLoggingMiddleware)

    # Include routers
    app.include_router(profiles_router, prefix="/users", tags=["User Profiles"])
    app.include_router(career_router, prefix="/users", tags=["Career Development"])
    app.include_router(analytics_router, prefix="/users", tags=["Learning Analytics"])
    app.include_router(achievements_router, prefix="/users", tags=["Achievements"])
    app.include_router(health_router, prefix="", tags=["Health"])

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "service": "User Service",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "profile": "/users/profile",
                "career_profile": "/users/career-profile",
                "study_plan": "/users/study-plan",
                "skill_gaps": "/users/skill-gaps",
                "career_readiness": "/users/career-readiness",
                "learning_analytics": "/users/learning-analytics",
                "achievements": "/users/achievements"
            }
        }

    return app

# Create application instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.environment == "development",
        log_level="info"
    )